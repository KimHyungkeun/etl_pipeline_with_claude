"""
PySpark Batch Job: Kafka에서 센서 데이터를 읽어 시간별 집계 후 Iceberg 테이블에 저장

[파이프라인 흐름]
    Kafka (sensor-raw 토픽)
           ↓
    Spark Structured Streaming + Trigger.AvailableNow()
           ↓
    JSON 파싱 → DataFrame 변환
           ↓
    1시간 윈도우 집계 (sensor_id, sensor_type, location별)
           ↓
    Iceberg 테이블 저장 (iceberg.iot.hourly_stats) - MERGE INTO
           ↓
    MinIO (S3) - Parquet 파일로 저장

[오프셋 관리]
    - 체크포인트(s3a://warehouse/checkpoints/batch_agg)에 오프셋 자동 저장
    - 다음 실행 시 마지막 처리 오프셋 이후부터 자동으로 이어서 처리
    - 중복 처리 방지

[실행 방법]
    # 로컬 모드
    spark-submit --master local[*] batch_aggregation.py

    # 클러스터 모드 (Spark Standalone)
    spark-submit --master spark://localhost:7077 batch_aggregation.py
"""

import logging
import os

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import from_json, col
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import (
    StructType,      # 스키마 정의용
    StructField,     # 필드 정의용
    StringType,      # 문자열 타입
    DoubleType,      # 실수 타입
)

# =============================================================================
# 로깅 설정
# =============================================================================
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "batch_aggregation.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# =============================================================================
# 설정값 (Configuration)
# =============================================================================

# Kafka 설정
KAFKA_BOOTSTRAP_SERVERS = "kafka-broker-1:29092"
KAFKA_TOPIC = "sensor-raw"

# MinIO (S3 호환 스토리지) 설정
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"

# Iceberg Catalog 설정
ICEBERG_WAREHOUSE = "s3a://warehouse/"
POSTGRES_JDBC_URL = "jdbc:postgresql://postgresql:5432/etl_db"
POSTGRES_USER = "etl_user"
POSTGRES_PASSWORD = "etl_password"

# 체크포인트 경로 (오프셋 저장)
CHECKPOINT_LOCATION = "s3a://warehouse/checkpoints/batch_agg"

# Iceberg 테이블명
ICEBERG_TABLE = "iceberg.iot.hourly_stats"

# =============================================================================
# 센서 데이터 스키마 정의
# =============================================================================
SENSOR_SCHEMA = StructType([
    StructField("sensor_id", StringType(), True),
    StructField("sensor_type", StringType(), True),
    StructField("location", StringType(), True),
    StructField("value", DoubleType(), True),
    StructField("unit", StringType(), True),
    StructField("timestamp", StringType(), True),
])


def create_spark_session() -> SparkSession:
    """
    SparkSession 생성 - Iceberg, Kafka, S3 연동 설정 포함
    """
    return (
        SparkSession.builder
        .appName("IoT Sensor Batch Aggregation")
        .config("spark.jars.packages", ",".join([
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3",
            "org.apache.hadoop:hadoop-aws:3.3.4",
            "software.amazon.awssdk:bundle:2.21.42",
            "org.postgresql:postgresql:42.7.3",
        ]))
        # Iceberg Catalog 설정
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.iceberg.type", "jdbc")
        .config("spark.sql.catalog.iceberg.uri", POSTGRES_JDBC_URL)
        .config("spark.sql.catalog.iceberg.jdbc.user", POSTGRES_USER)
        .config("spark.sql.catalog.iceberg.jdbc.password", POSTGRES_PASSWORD)
        .config("spark.sql.catalog.iceberg.warehouse", ICEBERG_WAREHOUSE)
        # S3/MinIO 설정
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )


def create_iceberg_tables(spark: SparkSession):
    """
    Iceberg 테이블 생성 (없으면 생성, 있으면 스킵)
    """
    spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.iot")

    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.iot.hourly_stats (
            window_start TIMESTAMP,
            window_end TIMESTAMP,
            sensor_id STRING,
            sensor_type STRING,
            location STRING,
            avg_value DOUBLE,
            min_value DOUBLE,
            max_value DOUBLE,
            stddev_value DOUBLE,
            reading_count BIGINT,
            processed_at TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(window_start), sensor_type)
    """)

    logger.info("Iceberg tables created/verified successfully")


def process_batch(batch_df: DataFrame, batch_id: int):
    """
    각 마이크로 배치를 처리하는 함수 (foreachBatch에서 호출)

    [처리 흐름]
    1. JSON 파싱
    2. 1시간 윈도우 집계
    3. MERGE INTO로 Iceberg 테이블에 Upsert
    """
    if batch_df.isEmpty():
        logger.info(f"Batch {batch_id}: No data to process")
        return

    spark = batch_df.sparkSession
    record_count = batch_df.count()
    logger.info(f"Batch {batch_id}: Processing {record_count} records")

    # ----- Step 1: JSON 파싱 -----
    parsed_df = (
        batch_df.select(
            from_json(col("value").cast("string"), SENSOR_SCHEMA).alias("data"),
            col("timestamp").alias("kafka_timestamp"),
        )
        .select("data.*", "kafka_timestamp")
    )

    # ----- Step 2: 1시간 윈도우 집계 (Spark SQL) -----
    parsed_df.createOrReplaceTempView("sensor_data")

    aggregated_df = spark.sql("""
        SELECT
            window.start AS window_start,
            window.end AS window_end,
            sensor_id,
            sensor_type,
            location,
            AVG(value) AS avg_value,
            MIN(value) AS min_value,
            MAX(value) AS max_value,
            STDDEV(value) AS stddev_value,
            COUNT(*) AS reading_count,
            current_timestamp() AS processed_at
        FROM sensor_data
        GROUP BY
            window(CAST(timestamp AS TIMESTAMP), '1 hour'),
            sensor_id,
            sensor_type,
            location
    """)

    # 집계 결과 미리보기
    logger.info(f"Batch {batch_id}: Aggregation result")
    aggregated_df.show(5, truncate=False)

    # ----- Step 3: MERGE INTO (Upsert) -----
    aggregated_df.createOrReplaceTempView("new_aggregated_data")

    spark.sql(f"""
        MERGE INTO {ICEBERG_TABLE} t
        USING new_aggregated_data s
        ON t.window_start = s.window_start
           AND t.sensor_id = s.sensor_id
           AND t.sensor_type = s.sensor_type
           AND t.location = s.location
        WHEN MATCHED THEN
            UPDATE SET
                window_end = s.window_end,
                avg_value = s.avg_value,
                min_value = s.min_value,
                max_value = s.max_value,
                stddev_value = s.stddev_value,
                reading_count = s.reading_count,
                processed_at = s.processed_at
        WHEN NOT MATCHED THEN
            INSERT *
    """)

    logger.info(f"Batch {batch_id}: Merged into {ICEBERG_TABLE}")


def main():
    """
    메인 실행 함수 - Structured Streaming + Trigger.AvailableNow()

    [동작 방식]
    1. Kafka에서 마지막 체크포인트 이후 데이터만 읽기
    2. 모든 가용 데이터 처리 후 자동 종료
    3. 오프셋을 체크포인트에 저장 (다음 실행 시 이어서 처리)
    """
    logger.info("Starting IoT Sensor Batch Aggregation Job")
    logger.info("=" * 50)

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        # 1. Iceberg 테이블 준비
        create_iceberg_tables(spark)

        # 2. Kafka Streaming 소스 설정
        logger.info("Setting up Kafka streaming source...")
        kafka_stream = (
            spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
            .option("subscribe", KAFKA_TOPIC)
            .option("startingOffsets", "earliest")  # 첫 실행 시만 적용 (체크포인트 없을 때)
            .load()
        )

        # 3. Streaming Query 실행 - Trigger.AvailableNow()
        # 현재 가용한 모든 데이터를 처리하고 종료
        logger.info("Starting streaming query with Trigger.AvailableNow()...")
        query: StreamingQuery = (
            kafka_stream.writeStream
            .foreachBatch(process_batch)
            .option("checkpointLocation", CHECKPOINT_LOCATION)
            .trigger(availableNow=True)  # 가용 데이터 처리 후 종료
            .start()
        )

        # 쿼리 완료 대기
        query.awaitTermination()

        logger.info("Batch job completed successfully!")
        logger.info(f"Checkpoint saved to: {CHECKPOINT_LOCATION}")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
# IoT Sensor Monitoring Pipeline

실시간/배치 데이터 처리 파이프라인 예제

## 아키텍처

```
[Python Generator]     센서 데이터 생성 (0.5초 간격)
       ↓
    [Kafka]           sensor-raw 토픽 (1 Broker, KRaft)
       ↓
┌──────┴──────┐
↓             ↓
[Flink]    [Spark]
실시간       배치
이상감지     시간별 집계
↓             ↓
└──────┬──────┘
       ↓
   [MinIO/S3]
   Iceberg 테이블 (Parquet) / 실시간 이상감지 파일 저장
       ↓
  [PostgreSQL]
  - Iceberg JDBC 카탈로그
  - 집계 결과 저장
```

## 디렉토리 구조

```
iot-pipeline/
├── generator/                    # Python 센서 데이터 생성기
│   ├── pyproject.toml
│   └── sensor_producer.py
├── flink-jobs/                   # Flink 실시간 처리 (Java/Maven)
│   ├── pom.xml
│   └── src/main/java/com/iot/pipeline/
│       ├── AnomalyDetectionJob.java
│       ├── SensorReading.java
│       └── AlertEvent.java
├── spark-jobs/
│   ├── pyspark-jobs/             # PySpark 배치 처리
│   │   ├── batch_aggregation.py
│   │   ├── batch_aggregation.log
│   │   └── pyproject.toml
│   └── scala-jobs/               # Scala Spark Job
│       ├── build.sbt
│       ├── project/
│       └── src/main/scala/com/example/
│           └── WordCount.scala
├── config/
│   └── init-postgresql.sql
└── scripts/
    ├── setup.sh
    ├── teardown.sh
    ├── create-kafka-topic.sh
    └── create-minio-bucket.sh
```

## 인프라 구성

```
etl-cluster/
├── docker-compose-kafka.yaml      # Kafka 1 Broker + Kafka UI
├── docker-compose-spark.yaml      # Spark Master + 1 Worker
├── docker-compose-flink.yaml      # Flink JobManager + 1 TaskManager
├── docker-compose-postgresql.yaml # PostgreSQL + pgAdmin
└── docker-compose-minio.yaml      # MinIO (S3 호환 스토리지)
```

## 실행 방법

### 1. 인프라 설정

```bash
# Docker 네트워크 생성
docker network create etl-network

# Kafka 볼륨 생성
docker volume create kafka-data-1
docker volume create kafka-secrets-1
docker volume create kafka-config-1

# 전체 컨테이너 실행
cd etl-cluster
docker compose -f docker-compose-kafka.yaml up -d
docker compose -f docker-compose-postgresql.yaml up -d
docker compose -f docker-compose-minio.yaml up -d
docker compose -f docker-compose-spark.yaml up -d
docker compose -f docker-compose-flink.yaml up -d

# PostgreSQL 초기화 (Iceberg 카탈로그 테이블)
docker exec -i postgresql psql -U etl_user -d etl_db < config/init-postgresql.sql

# Kafka 토픽 생성
docker exec kafka-broker-1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker-1:29092 \
  --create --topic sensor-raw \
  --partitions 1 --replication-factor 1
```

### 2. /etc/hosts 설정 (호스트에서 Docker 서비스 접근용)

```bash
# Docker 컨테이너명을 localhost로 매핑
echo "127.0.0.1 postgresql kafka-broker-1 spark-master minio" | sudo tee -a /etc/hosts
```

### 3. 센서 데이터 생성

```bash
cd generator
poetry install
poetry run python sensor_producer.py
```

### 4. PySpark Batch Job 실행

```bash
cd spark-jobs/pyspark-jobs

# 로컬 모드 실행 (권장)
spark-submit --master local[*] batch_aggregation.py

# 클라이언트 모드 실행
spark-submit \
  --master spark://localhost:7077 \
  --deploy-mode client \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.hadoop:hadoop-aws:3.3.4,software.amazon.awssdk:bundle:2.21.42,org.postgresql:postgresql:42.7.3 \
  batch_aggregation.py
```

### 5. Scala WordCount Job 실행

```bash
cd spark-jobs/scala-jobs

# 빌드 (SBT 필요)
sbt assembly

# 실행
spark-submit \
  --class com.example.WordCount \
  --master local[*] \
  target/scala-2.12/spark-wordcount-assembly-1.0.0.jar
```

### 6. Flink Job 실행

```bash
cd flink-jobs
mvn clean package

# Flink JobManager에 제출
docker cp target/flink-anomaly-detection-1.0.0.jar flink-jobmanager:/opt/flink/
docker exec flink-jobmanager flink run /opt/flink/flink-anomaly-detection-1.0.0.jar
```

## Iceberg 테이블 조회

```bash
spark-sql \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.hadoop:hadoop-aws:3.3.4,software.amazon.awssdk:bundle:2.21.42,org.postgresql:postgresql:42.7.3 \
  --conf spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.iceberg.type=jdbc \
  --conf spark.sql.catalog.iceberg.uri=jdbc:postgresql://postgresql:5432/etl_db \
  --conf spark.sql.catalog.iceberg.jdbc.user=etl_user \
  --conf spark.sql.catalog.iceberg.jdbc.password=etl_password \
  --conf spark.sql.catalog.iceberg.warehouse=s3a://warehouse/ \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minioadmin \
  --conf spark.hadoop.fs.s3a.secret.key=minioadmin123 \
  --conf spark.hadoop.fs.s3a.path.style.access=true
```

```sql
-- 테이블 조회
SHOW TABLES IN iceberg.iot;
SELECT * FROM iceberg.iot.hourly_stats LIMIT 10;

-- 테이블 삭제
DROP TABLE IF EXISTS iceberg.iot.hourly_stats PURGE;
```

## 서비스 URL

| 서비스 | URL | 비고 |
|--------|-----|------|
| Kafka | localhost:9092 (외부), 29092 (내부) | KRaft 모드 |
| Kafka UI | http://localhost:9090 | |
| Flink UI(미사용) | http://localhost:8083 | |
| Spark Master UI | http://localhost:8080 | |
| PostgreSQL | localhost:5432 | etl_user / etl_password |
| pgAdmin | http://localhost:5050 | admin@admin.com / admin |
| MinIO API | http://localhost:9000 | minioadmin / minioadmin123 |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |

## 센서 데이터 형식

```json
{
    "sensor_id": "TEMP-001",
    "sensor_type": "temperature",
    "location": "building_A",
    "value": 25.5,
    "unit": "celsius",
    "timestamp": "2024-12-08T12:00:00Z"
}
```

## 센서 타입별 임계값

| 센서 타입 | 정상 범위 | 단위 |
|-----------|-----------|------|
| temperature | 20.0 ~ 30.0 | celsius |
| humidity | 40.0 ~ 70.0 | percent |
| pressure | 1000.0 ~ 1020.0 | hPa |

## 기술 스택

| 구성요소 | 버전 | 비고 |
|----------|------|------|
| Apache Kafka | 3.9.1 | KRaft 모드 (No Zookeeper) |
| Apache Spark | 3.5.3 | Standalone 클러스터 |
| Apache Flink | 1.18 | Java 11 |
| Apache Iceberg | 1.5.2 | JDBC 카탈로그 (PostgreSQL) |
| PostgreSQL | 15 | Iceberg 메타데이터 저장 |
| MinIO | latest | S3 호환 스토리지 |
| Python | 3.11+ | PySpark, Generator |
| Scala | 2.12 | Spark Scala Jobs |

## 정리

```bash
# 모든 컨테이너 중지
cd etl-cluster
docker compose -f docker-compose-kafka.yaml down
docker compose -f docker-compose-spark.yaml down
docker compose -f docker-compose-flink.yaml down
docker compose -f docker-compose-postgresql.yaml down
docker compose -f docker-compose-minio.yaml down

# 볼륨 삭제 (데이터 삭제 시)
docker volume rm kafka-data-1 kafka-secrets-1 kafka-config-1

# 네트워크 삭제
docker network rm etl-network
```

## 로그 확인

```bash
# PySpark Job 로그
tail -f spark-jobs/pyspark-jobs/batch_aggregation.log

# Kafka 토픽 메시지 수 확인
docker exec kafka-broker-1 /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server kafka-broker-1:29092 --topic sensor-raw

# Docker 컨테이너 로그
docker logs -f kafka-broker-1
docker logs -f spark-master
docker logs -f flink-jobmanager
```
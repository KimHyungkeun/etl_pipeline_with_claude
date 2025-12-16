# Spark Jobs - IoT Batch Aggregation

## 개요

Kafka에서 IoT 센서 데이터를 배치로 읽어와 시간별 집계 후 Iceberg 테이블(MinIO)에 저장하는 PySpark Batch Job입니다.

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│  Kafka (sensor-raw Topic)                                        │
│  - 체크포인트에서 마지막으로 읽은 오프셋부터 시작                    │
│  - 첫 실행 시에만 earliest부터 시작                               │
└──────────────────────────┬───────────────────────────────────────┘
                           │ JSON 메시지
                           │ {"sensor_id":"TEMP-001","value":35.5,...}
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  1. Structured Streaming (Trigger.AvailableNow)                 │
│     - kafka.bootstrap.servers: kafka-broker-1:29092              │
│     - startingOffsets: earliest (첫 실행 시만 적용)               │
│     - checkpointLocation: s3a://warehouse/checkpoints/batch_agg  │
│     - 이후 실행: 체크포인트의 마지막 오프셋부터 자동 이어서 처리      │
└──────────────────────────┬───────────────────────────────────────┘
                           │ DataFrame (binary value)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. process_and_aggregate()                                      │
│     ┌────────────────────────────────────────────────────────┐   │
│     │ Step 1: JSON 파싱                                       │   │
│     │   value (binary) → string → from_json() → DataFrame    │   │
│     │                                                         │   │
│     │ Step 2: 1시간 윈도우 집계 (Spark SQL)                    │   │
│     │   GROUP BY: window(timestamp, '1 hour'),                │   │
│     │             sensor_id, sensor_type, location            │   │
│     │                                                         │   │
│     │ 집계 함수:                                               │   │
│     │   - AVG(value)   → avg_value                            │   │
│     │   - MIN(value)   → min_value                            │   │
│     │   - MAX(value)   → max_value                            │   │
│     │   - STDDEV(value)→ stddev_value                         │   │
│     │   - COUNT(*)     → reading_count                        │   │
│     └────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Aggregated DataFrame
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. write_to_iceberg()                                           │
│     - 테이블: iceberg.iot.hourly_stats                           │
│     - 모드: Append                                               │
│     - merge-schema: true                                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│      PostgreSQL         │     │        MinIO            │
│  (Iceberg Catalog)      │     │   (Data Storage)        │
│                         │     │                         │
│  - 테이블 메타데이터      │     │  s3a://warehouse/       │
│  - 스키마 정보           │     │   └── iot/              │
│  - 파티션 정보           │     │       └── hourly_stats/ │
│  - 스냅샷 히스토리        │     │           └── data/     │
│                         │     │               └── *.parquet│
└─────────────────────────┘     └─────────────────────────┘
```

## 프로젝트 구조

```
spark-jobs/
├── README.md
├── pyspark-jobs/
│   ├── batch_aggregation.py     # 메인 배치 Job
│   ├── batch_aggregation.log    # 실행 로그
│   └── pyproject.toml           # Poetry 의존성
└── unused/                      # 미사용 코드
    └── scala-jobs/              # Scala 예제 (참고용)
```

## 사전 요구사항

- Kafka 클러스터 실행 중 (`sensor-raw` 토픽 존재)
- MinIO 실행 중 (`warehouse` 버킷 존재)
- PostgreSQL 실행 중 (Iceberg 카탈로그용)
- Spark 클러스터 실행 중 (선택적 - 로컬 모드 가능)

## 실행 방법

### 로컬 모드 (Poetry 환경)

```bash
cd ${HOME}/etl-cluster-test/iot-pipeline/spark-jobs/pyspark-jobs

# Poetry 환경 활성화
poetry install
poetry shell

# 실행
spark-submit --master local[*] batch_aggregation.py
```

### 클러스터 모드 (Spark Standalone)

```bash
# Spark Master 컨테이너에서 실행
docker exec -it spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/pyspark-jobs/batch_aggregation.py
```

### 호스트에서 클러스터 제출

```bash
spark-submit \
  --master spark://localhost:7077 \
  ${HOME}/etl-cluster-test/iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.py
```

## 설정

### Kafka 설정

| 설정 | 값 | 설명 |
|------|-----|------|
| bootstrap.servers | kafka-broker-1:29092 | Kafka 브로커 주소 |
| topic | sensor-raw | 구독 토픽 |
| startingOffsets | earliest | 시작 오프셋 (첫 실행 시만 적용) |
| checkpointLocation | s3a://warehouse/checkpoints/batch_agg | 오프셋 저장 위치 |

**오프셋 관리:**
- 첫 실행: `earliest`부터 시작하여 모든 데이터 처리
- 이후 실행: 체크포인트에 저장된 마지막 오프셋부터 자동으로 이어서 처리
- 중복 처리 방지 및 정확히 한 번(exactly-once) 처리 보장

### MinIO 설정

| 설정 | 값 | 설명 |
|------|-----|------|
| endpoint | http://minio:9000 | MinIO 서버 주소 |
| access.key | minioadmin | 액세스 키 |
| secret.key | minioadmin123 | 시크릿 키 |
| path.style.access | true | Path-style 접근 (MinIO 필수) |

### Iceberg Catalog 설정

| 설정 | 값 | 설명 |
|------|-----|------|
| catalog type | jdbc | PostgreSQL 기반 카탈로그 |
| jdbc.uri | jdbc:postgresql://postgresql:5432/etl_db | DB 연결 문자열 |
| jdbc.user | etl_user | DB 사용자 |
| warehouse | s3a://warehouse/ | 데이터 저장 경로 |

## Iceberg 테이블 스키마

### iceberg.iot.hourly_stats

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| window_start | TIMESTAMP | 집계 윈도우 시작 |
| window_end | TIMESTAMP | 집계 윈도우 종료 |
| sensor_id | STRING | 센서 ID |
| sensor_type | STRING | 센서 종류 |
| location | STRING | 설치 위치 |
| avg_value | DOUBLE | 평균값 |
| min_value | DOUBLE | 최소값 |
| max_value | DOUBLE | 최대값 |
| stddev_value | DOUBLE | 표준편차 |
| reading_count | BIGINT | 측정 횟수 |
| processed_at | TIMESTAMP | 처리 시각 |

**파티셔닝**: `days(window_start)`, `sensor_type`

## 데이터 흐름 예시

### 입력 (Kafka sensor-raw)

```json
{
  "sensor_id": "TEMP-001",
  "sensor_type": "temperature",
  "location": "factory-A",
  "value": 25.5,
  "unit": "celsius",
  "timestamp": "2025-12-09T10:30:00Z"
}
```

### 출력 (Iceberg hourly_stats)

```
+-------------------+-------------------+---------+------------+----------+---------+---------+---------+------------+-------------+-------------------+
|window_start       |window_end         |sensor_id|sensor_type |location  |avg_value|min_value|max_value|stddev_value|reading_count|processed_at       |
+-------------------+-------------------+---------+------------+----------+---------+---------+---------+------------+-------------+-------------------+
|2025-12-09 10:00:00|2025-12-09 11:00:00|TEMP-001 |temperature |factory-A |25.3     |20.1     |30.5     |2.15        |120          |2025-12-09 11:05:00|
+-------------------+-------------------+---------+------------+----------+---------+---------+---------+------------+-------------+-------------------+
```

## 모니터링

- Spark Master UI: http://localhost:8080

## 로그 확인

```bash
# 실행 로그
cat ${HOME}/etl-cluster-test/iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.log

# 실시간 로그 모니터링
tail -f ${HOME}/etl-cluster-test/iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.log
```

## 의존성

### Maven (spark-submit 시 자동 다운로드)

- org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2
- org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3
- org.apache.hadoop:hadoop-aws:3.3.4
- software.amazon.awssdk:bundle:2.21.42
- org.postgresql:postgresql:42.7.3

### Python (Poetry)

- Python ^3.11
- PySpark ^3.5.0

## 주의사항

### 호스트에서 실행 시

`/etc/hosts`에 다음 항목 추가 필요:

```
127.0.0.1 kafka-broker-1
127.0.0.1 spark-master
127.0.0.1 minio
127.0.0.1 postgresql
```

### Derby 메타스토어

로컬 실행 시 `metastore_db/` 폴더가 자동 생성됩니다. 이는 Derby 내장 DB이며 삭제해도 무방합니다.

`.gitignore`에 추가 권장:
```
metastore_db/
derby.log
*.log
```
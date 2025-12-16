# Flink Jobs - IoT Anomaly Detection

## 개요

IoT 센서 데이터에서 이상치를 실시간으로 감지하여 MinIO에 알림 파일로 저장하는 Flink Streaming Job입니다.

## 아키텍처

```
┌──────────────┐
│    Kafka     │
│  sensor-raw  │
│    Topic     │
└──────┬───────┘
       │ JSON 메시지
       │ {"sensor_id":"TEMP-001","sensor_type":"temperature","value":35.5,...}
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  1. KafkaSource (OffsetsInitializer.latest())                    │
│     - kafka-broker-1:29092 연결                                   │
│     - consumer group: flink-anomaly-detection                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │ String (raw JSON)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. JsonToSensorReading (MapFunction)                            │
│     - JSON 파싱 → SensorReading 객체 변환                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │ SensorReading
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. AnomalyFilter (FilterFunction)                               │
│     - 센서 타입별 임계값 기준 이상치 필터링                          │
│       ┌────────────────────────────────────────┐                 │
│       │ temperature: 20.0 ~ 30.0               │                 │
│       │ humidity:    40.0 ~ 70.0               │                 │
│       │ pressure:    1000.0 ~ 1020.0           │                 │
│       └────────────────────────────────────────┘                 │
│     - value < min OR value > max → 이상치 (통과)                  │
│     - 정상 범위 내 → 필터링 (제거)                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ SensorReading (이상치만)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. CreateAlert (MapFunction)                                    │
│     - SensorReading → AlertEvent 변환                             │
│     - alertType: "HIGH" or "LOW"                                 │
│     - threshold: 초과한 임계값                                     │
└──────────────────────────┬───────────────────────────────────────┘
                           │ AlertEvent
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│  5a. AlertToJson        │   │  5b. print("ALERT")     │
│      → JSON String      │   │      콘솔 출력 (디버깅)   │
└───────────┬─────────────┘   └─────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. FileSink (MinIO S3)                                          │
│     - Path: s3a://flinkalert/alert                               │
│     - 날짜별 폴더: /alert/2025-12-09/                              │
│     - 파일명: alert-0-0.json                                      │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                         MinIO                                     │
│  Bucket: flinkalert                                               │
│  └── alert/                                                       │
│      └── 2025-12-09/                                              │
│          ├── alert-0-0.json                                       │
│          └── alert-0-1.json                                       │
└──────────────────────────────────────────────────────────────────┘
```

## 프로젝트 구조

```
flink-jobs/
├── pom.xml
├── README.md
└── src/main/java/com/iot/pipeline/
    ├── AnomalyDetectionJob.java    # 메인 Job 클래스
    └── dto/
        ├── AlertEvent.java         # 알림 이벤트 DTO
        └── SensorReading.java      # 센서 데이터 DTO
```

## 빌드

```bash
cd /home/hkkim/etl-cluster-test/iot-pipeline/flink-jobs
mvn clean package -DskipTests
```

빌드 결과: `target/flink-anomaly-detection-1.0.0.jar`

## 실행

### 사전 요구사항

- Kafka 클러스터 실행 중 (`sensor-raw` 토픽 존재)
- MinIO 실행 중 (`flinkalert` 버킷 존재)
- Flink 클러스터 실행 중

### Job 제출

```bash
docker exec -it flink-jobmanager flink run /opt/flink/flink-anomaly-detection-1.0.0.jar
```

### Job 상태 확인

- Flink Web UI: http://localhost:8083

### Job 취소

```bash
docker exec -it flink-jobmanager flink cancel <job-id>
```

## 설정

### 임계값 (Thresholds)

| 센서 타입 | 정상 최소값 | 정상 최대값 |
|-----------|-------------|-------------|
| temperature | 20.0 | 30.0 |
| humidity | 40.0 | 70.0 |
| pressure | 1000.0 | 1020.0 |

### FileSink 설정

| 설정 | 값 | 설명 |
|------|-----|------|
| RolloverInterval | 5분 | 5분마다 새 파일 생성 |
| InactivityInterval | 2분 | 2분간 데이터 없으면 롤오버 |
| MaxPartSize | 1MB | 파일 크기 1MB 초과 시 롤오버 |

### 체크포인트

- 간격: 60초 (1분)
- 파일은 체크포인트 완료 후 커밋됨

## 파일 상태

FileSink는 파일 작성 상태에 따라 파일명이 변경됩니다:

| 상태 | 파일명 예시 | 설명 |
|------|-------------|------|
| 작성 중 | `_alert-xxx.json_tmp_xxx` | 데이터 작성 중 |
| 완료 | `alert-0-0.json` | 체크포인트 후 커밋됨 |

## 데이터 흐름 예시

### 입력 (Kafka sensor-raw)

```json
{
  "sensor_id": "TEMP-001",
  "sensor_type": "temperature",
  "location": "factory-A",
  "value": 35.5,
  "unit": "celsius",
  "timestamp": "2025-12-09T10:30:00Z"
}
```

### 출력 (MinIO JSON 파일)

```json
{
  "alertId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "sensorId": "TEMP-001",
  "sensorType": "temperature",
  "location": "factory-A",
  "value": 35.5,
  "unit": "celsius",
  "alertType": "HIGH",
  "threshold": 30.0,
  "timestamp": "2025-12-09T10:30:00Z",
  "detectedAt": "2025-12-09T10:30:01Z"
}
```

## 의존성

- Flink 1.18.1
- Flink Kafka Connector 3.1.0-1.18
- Flink S3 FS Hadoop
- Jackson Databind 2.15.3
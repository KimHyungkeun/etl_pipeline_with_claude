# IoT 센서 모니터링 파이프라인 - 인수인계 문서

> **작성일**: 2025-12-11
> **대상**: 백엔드 개발자 (Python/FastAPI 경험자, 빅데이터 파이프라인 신규 학습자)
> **목적**: 프로젝트 전체 구조 이해 및 로컬 환경 구축·운영 가이드

---

## 📑 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [아키텍처](#2-아키텍처)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [로컬 환경 구축](#4-로컬-환경-구축)
5. [시스템 운영](#5-시스템-운영)
6. [데이터 파이프라인 실행](#6-데이터-파이프라인-실행)
7. [API 서버 사용](#7-api-서버-사용)
8. [확장 및 커스터마이징](#8-확장-및-커스터마이징)
9. [트러블슈팅](#9-트러블슈팅)
10. [기술 스택 상세](#10-기술-스택-상세)
11. [참고 자료](#11-참고-자료)

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적

IoT 센서 데이터(온도, 습도, 압력)를 **실시간으로 수집·처리·저장**하고, **REST API와 웹 UI**를 통해 모니터링하는 데이터 파이프라인 프로젝트입니다.

**주요 기능**:
- 센서 데이터 0.5초 간격 실시간 생성 (Python Generator)
- Kafka를 통한 메시지 스트리밍
- Spark를 통한 시간별 배치 집계 처리
- Apache Iceberg 테이블로 데이터 저장 (MinIO S3 + PostgreSQL 카탈로그)
- FastAPI 기반 REST API 서버로 Spark 클러스터 모니터링 및 Job 제출
- React 기반 웹 UI로 시각화

### 1.2 전체 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Pipeline                             │
└─────────────────────────────────────────────────────────────────┘

[Python Generator]  ─────▶  [Kafka: sensor-raw]
   (센서 데이터 생성)            (메시지 브로커)
   0.5초 간격                    │
                                 │
                       ┌─────────┴─────────┐
                       │                   │
                       ▼                   ▼
                  [Spark]              [Flink]
                배치 처리              (미사용)
              시간별 집계
                       │
                       ▼
              [MinIO S3 Storage]
           Apache Iceberg Tables
              (Parquet 포맷)
                       │
                       ▼
              [PostgreSQL]
           - Iceberg 카탈로그
           - 집계 결과 저장


┌─────────────────────────────────────────────────────────────────┐
│                   Management & Monitoring                        │
└─────────────────────────────────────────────────────────────────┘

[spark-fastapi]  ◀────▶  [Spark Cluster]
  FastAPI REST API         (Master + Workers)
        │
        │ HTTP
        ▼
[spark-fastapi-ui]
  React Web UI
```

### 1.3 주요 컴포넌트 요약

| 컴포넌트 | 역할 | 기술 스택 |
|---------|------|----------|
| **iot-pipeline/generator** | 센서 데이터 생성기 | Python 3.11, kafka-python |
| **iot-pipeline/spark-jobs** | 배치 데이터 집계 | PySpark 3.5.3, Apache Iceberg |
| **etl-cluster** | 인프라 환경 | Docker Compose (Kafka, Spark, PostgreSQL, MinIO) |
| **spark-fastapi** | Spark 클러스터 관리 API | FastAPI, httpx, Pydantic |
| **spark-fastapi-ui** | 웹 모니터링 대시보드 | React, TypeScript, Vite |

---

## 2. 아키텍처

### 2.1 데이터 플로우

#### 📊 전체 데이터 흐름

```
1. 데이터 생성
   └─▶ Python Generator가 센서 데이터를 JSON 형태로 생성
       (온도, 습도, 압력 센서 3종류)

2. 메시지 스트리밍
   └─▶ Kafka Topic(sensor-raw)에 Publish
       - 메시지 포맷: JSON
       - 파티션: 1개 (테스트 환경)

3. 배치 처리
   └─▶ Spark Job이 Kafka Topic에서 데이터 읽기
       - 시간별(hourly) 집계: AVG, MIN, MAX, COUNT
       - 센서별, 위치별 그룹핑

4. 데이터 저장
   └─▶ Apache Iceberg 테이블에 저장
       - 파일 포맷: Parquet (컬럼형 압축)
       - 스토리지: MinIO (S3 호환)
       - 메타데이터: PostgreSQL JDBC 카탈로그

5. 조회 및 모니터링
   └─▶ Spark SQL로 Iceberg 테이블 쿼리
       └─▶ FastAPI로 Spark 클러스터 상태 모니터링
           └─▶ React UI로 시각화
```

### 2.2 컴포넌트별 역할

#### 🔹 Apache Kafka (메시지 브로커)
**왜 필요한가?**
센서 데이터를 실시간으로 수집·전송하려면 생성자(Producer)와 소비자(Consumer)를 분리해야 합니다. Kafka는 이 중간에서 메시지를 버퍼링하고, 여러 Consumer(Spark, Flink 등)가 독립적으로 데이터를 읽을 수 있게 해줍니다.

**주요 특징**:
- Topic 기반 Pub/Sub 모델
- 높은 처리량 (수만 메시지/초)
- 메시지 영속성 (디스크 저장)
- KRaft 모드 사용 (Zookeeper 불필요)

**이 프로젝트에서의 역할**:
- `sensor-raw` Topic에 센서 데이터 스트리밍
- Spark Consumer가 배치 단위로 데이터 읽기

#### 🔹 Apache Spark (분산 처리 엔진)
**왜 필요한가?**
대량의 센서 데이터를 시간별로 집계하려면 단일 서버로는 처리 속도가 느립니다. Spark는 데이터를 여러 Worker에 분산시켜 병렬 처리하며, 메모리 기반으로 빠른 성능을 제공합니다.

**주요 특징**:
- 인메모리 분산 처리 (MapReduce보다 빠름)
- Structured Streaming / Batch 처리 지원
- Scala, Python, Java API 제공

**이 프로젝트에서의 역할**:
- Kafka Topic에서 센서 데이터 읽기
- 시간별(hourly) 집계 쿼리 실행
- Iceberg 테이블에 결과 저장

**Standalone 클러스터 구성**:
- **Master**: 스케줄링 및 Worker 관리
- **Worker**: 실제 데이터 처리 수행
- **Driver**: Job 제출 및 실행 계획 수립

#### 🔹 Apache Iceberg (테이블 포맷)
**왜 필요한가?**
Parquet 파일을 직접 다루면 스키마 변경, 파티션 관리, ACID 트랜잭션이 어렵습니다. Iceberg는 이런 문제를 해결하는 오픈 테이블 포맷으로, **데이터 레이크를 마치 DB처럼** 사용할 수 있게 해줍니다.

**주요 특징**:
- 스키마 진화 (Schema Evolution)
- Hidden Partitioning (파티션 자동 관리)
- Time Travel (과거 스냅샷 조회)
- ACID 트랜잭션

**이 프로젝트에서의 역할**:
- Spark 집계 결과를 `iot.hourly_stats` 테이블로 저장
- PostgreSQL이 메타데이터(스키마, 파티션 정보) 관리
- MinIO가 실제 Parquet 데이터 파일 저장

#### 🔹 MinIO (S3 호환 스토리지)
**왜 필요한가?**
AWS S3는 유료이고 로컬 테스트가 어렵습니다. MinIO는 S3 API와 호환되는 오픈소스 객체 스토리지로, 로컬 환경에서 S3와 동일하게 동작합니다.

**이 프로젝트에서의 역할**:
- `warehouse/` 버킷에 Iceberg Parquet 파일 저장
- Spark가 s3a 프로토콜로 접근

#### 🔹 PostgreSQL (메타데이터 카탈로그)
**왜 필요한가?**
Iceberg는 테이블 메타데이터(스키마, 파티션, 스냅샷 이력)를 어딘가에 저장해야 합니다. PostgreSQL JDBC 카탈로그는 이 메타데이터를 관리하고, 여러 Spark Job이 동시에 테이블을 안전하게 읽고 쓸 수 있게 해줍니다.

**이 프로젝트에서의 역할**:
- Iceberg 카탈로그 메타데이터만 저장 (`iceberg_tables`, `iceberg_namespace_properties` 테이블)
- 실제 센서 집계 데이터는 MinIO에 Parquet 파일로 저장

#### 🔹 spark-fastapi (관리 API 서버)
**이 프로젝트에서의 역할**:
- Spark Master REST API를 Wrapping하여 사용자 친화적인 API 제공
- 클러스터 상태 모니터링 (코어, 메모리, Worker, 애플리케이션)
- Spark Job 제출 및 실행 중인 애플리케이션 종료
- CORS 설정으로 프론트엔드와 통신

**주요 API 엔드포인트**:
- `GET /api/v1/cluster/status` - 클러스터 상태
- `GET /api/v1/cluster/workers` - Worker 정보
- `GET /api/v1/jobs/apps` - 애플리케이션 목록
- `POST /api/v1/jobs/submit` - Job 제출
- `DELETE /api/v1/jobs/apps/{app_id}` - 애플리케이션 종료

#### 🔹 spark-fastapi-ui (웹 대시보드)
**이 프로젝트에서의 역할**:
- spark-fastapi API를 통해 Spark 클러스터 시각화
- 클러스터 리소스 사용량 모니터링
- 실행 중인 Job 확인 및 관리

### 2.3 네트워크 및 포트 구성

| 서비스 | 포트 | 용도 |
|--------|------|------|
| Kafka Broker | 9092 (외부), 29092 (내부) | Producer/Consumer 연결 |
| Kafka UI | 9090 | Kafka 토픽 모니터링 웹 UI |
| Spark Master UI | 8080 | 클러스터 상태 확인 |
| Spark Master | 7077 | Spark Job 제출 |
| PostgreSQL | 5432 | JDBC 연결 |
| pgAdmin | 5050 | PostgreSQL 관리 UI |
| MinIO API | 9000 | S3 호환 API |
| MinIO Console | 9001 | MinIO 관리 UI |
| spark-fastapi | 8000 | REST API 서버 |
| spark-fastapi-ui | 5173 | React 개발 서버 |

**Docker 네트워크**: 모든 컨테이너는 `etl-network` 브릿지 네트워크로 통신합니다.

---

## 3. 디렉토리 구조

### 3.1 전체 프로젝트 구조

```
etl-cluster-test/
├── etl-cluster/              # 인프라 Docker Compose 파일
│   ├── docker-compose-kafka.yaml
│   ├── docker-compose-spark.yaml
│   ├── docker-compose-postgresql.yaml
│   └── docker-compose-minio.yaml
│
├── scripts/                  # 통합 셋업/관리 스크립트
│   ├── setup.sh              # 전체 환경 자동 설정
│   ├── teardown.sh           # 전체 환경 종료
│   ├── create-kafka-topic.sh # Kafka 토픽 생성
│   └── create-minio-bucket.sh # MinIO 버킷 생성
│
├── iot-pipeline/             # 데이터 파이프라인
│   ├── generator/            # 센서 데이터 생성기
│   │   ├── pyproject.toml
│   │   └── sensor_producer.py
│   ├── spark-jobs/           # Spark 데이터 처리
│   │   └── pyspark-jobs/
│   │       ├── batch_aggregation.py
│   │       └── pyproject.toml
│   ├── flink-jobs/           # (미사용)
│   └── config/
│       └── init-postgresql.sql
│
├── spark-fastapi/            # FastAPI 관리 서버
│   ├── app/
│   │   ├── api/endpoints/
│   │   │   ├── cluster.py    # 클러스터 모니터링
│   │   │   └── jobs.py       # Job 관리
│   │   ├── core/config.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   └── spark_client.py
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── pyproject.toml
│   └── pytest.ini
│
├── spark-fastapi-ui/         # React 웹 UI
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── shared/api/
│   ├── package.json
│   └── vite.config.ts
│
├── TESTING.md                # 테스트 가이드
└── HANDOVER.md               # 이 문서
```

### 3.2 주요 파일 설명

#### 데이터 파이프라인

| 파일 경로 | 설명 |
|----------|------|
| `iot-pipeline/generator/sensor_producer.py` | Kafka Producer로 센서 데이터 생성 (0.5초 간격) |
| `iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.py` | Kafka → Spark → Iceberg 배치 처리 Job |
| `iot-pipeline/config/init-postgresql.sql` | PostgreSQL 초기 스키마 (Iceberg 카탈로그) |

#### API 서버

| 파일 경로 | 설명 |
|----------|------|
| `spark-fastapi/app/main.py` | FastAPI 애플리케이션 진입점 |
| `spark-fastapi/app/services/spark_client.py` | Spark Master REST API 클라이언트 |
| `spark-fastapi/app/api/endpoints/cluster.py` | 클러스터 상태, Worker 조회 API |
| `spark-fastapi/app/api/endpoints/jobs.py` | Job 제출, 앱 목록, 앱 종료 API |

#### 웹 UI

| 파일 경로 | 설명 |
|----------|------|
| `spark-fastapi-ui/src/shared/api/spark.ts` | API 클라이언트 (fetch 래퍼) |
| `spark-fastapi-ui/src/pages/ClusterPage.tsx` | 클러스터 모니터링 페이지 |
| `spark-fastapi-ui/src/pages/AppsPage.tsx` | 애플리케이션 목록 페이지 |

---

## 4. 로컬 환경 구축

### 4.1 사전 요구사항

**필수 소프트웨어**:
- Docker (버전 20.10 이상)
- Docker Compose (버전 2.0 이상)
- Python 3.11 이상
- Poetry (Python 패키지 관리)
- Apache Spark 3.5.3 (로컬에 설치)
- Node.js 18 이상 (프론트엔드용)

**확인 명령어**:
```bash
docker --version
docker compose --version
python --version
poetry --version
spark-submit --version
node --version
```

### 4.2 Apache Spark 설치

#### Spark 3.5.3 다운로드 및 설치

```bash
# 1. HOME 디렉토리로 이동
cd ${HOME}

# 2. Apache Spark 3.5.3 다운로드
wget https://archive.apache.org/dist/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz

# 3. 압축 해제
tar -xzf spark-3.5.3-bin-hadoop3.tgz

# 4. 심볼릭 링크 생성 (spark → spark-3.5.3-bin-hadoop3)
ln -s ${HOME}/spark-3.5.3-bin-hadoop3 ${HOME}/spark

# 5. 다운로드 파일 정리 (선택)
rm spark-3.5.3-bin-hadoop3.tgz
```

#### 환경 변수 설정

`~/.bashrc` 또는 `~/.zshrc`에 다음 추가:

```bash
export SPARK_HOME=${HOME}/spark
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
```

설정 적용:
```bash
source ~/.bashrc  # 또는 source ~/.zshrc
```

#### 설치 확인

```bash
spark-submit --version
# Spark 3.5.3이 출력되면 설치 완료
```

### 4.3 환경 변수 설정

#### spark-fastapi/.env
```env
SPARK_MASTER_URL=http://localhost:8080
SPARK_SUBMIT_MASTER=spark://localhost:7077
SPARK_HOME=${HOME}/spark
```

#### /etc/hosts 설정 (로컬에서 Docker 컨테이너 이름 접근)
```bash
sudo tee -a /etc/hosts <<EOF
127.0.0.1 postgresql
127.0.0.1 kafka-broker-1
127.0.0.1 spark-master
127.0.0.1 minio
EOF
```

### 4.4 단계별 설치 가이드

#### 🚀 자동 설정 (권장)

**한 번에 모든 환경 설정**:
```bash
cd ${HOME}/etl-cluster-test
./scripts/setup.sh
```

이 스크립트는 자동으로 다음 작업을 수행합니다:
- Docker 네트워크 생성
- Docker 볼륨 생성
- MinIO 데이터 디렉토리 생성
- 모든 Docker 컨테이너 실행 (Kafka, Spark, PostgreSQL, MinIO)
- PostgreSQL 초기화 (Iceberg 카탈로그 테이블 생성)

**다음 단계**:
```bash
# 1. Kafka 토픽 생성
./scripts/create-kafka-topic.sh

# 2. MinIO 버킷 생성
./scripts/create-minio-bucket.sh
```

#### 📋 수동 설정 (선택)

**Step 1: Docker 네트워크 및 볼륨 생성**

```bash
# 네트워크 생성
docker network create etl-network

# Kafka 볼륨 생성
docker volume create kafka-data-1
docker volume create kafka-secrets-1
docker volume create kafka-config-1
```

**Step 2: 인프라 컨테이너 실행 (순서 중요)**

```bash
cd etl-cluster

# 1. PostgreSQL 실행 (Iceberg 카탈로그용)
docker compose -f docker-compose-postgresql.yaml up -d

# 2. MinIO 실행 (S3 스토리지용)
docker compose -f docker-compose-minio.yaml up -d

# 3. Kafka 실행 (메시지 브로커)
docker compose -f docker-compose-kafka.yaml up -d

# 4. Spark 클러스터 실행
docker compose -f docker-compose-spark.yaml up -d

# 컨테이너 상태 확인
docker ps
```

**기대 출력**: 8개 컨테이너 실행 (kafka-broker-1, kafka-ui, postgresql, pgadmin, minio, spark-master, spark-worker-1)

**Step 3: PostgreSQL 초기화**

```bash
cd ../iot-pipeline
docker exec -i postgresql psql -U etl_user -d etl_db < config/init-postgresql.sql
```

**Step 4: Kafka 토픽 생성**

```bash
docker exec kafka-broker-1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker-1:29092 \
  --create --topic sensor-raw \
  --partitions 1 --replication-factor 1
```

**검증**:
```bash
docker exec kafka-broker-1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker-1:29092 \
  --list
```

**Step 5: MinIO 버킷 생성**

1. MinIO Console 접속: http://localhost:9001
2. 로그인: `minioadmin` / `minioadmin123`
3. Buckets 메뉴에서 `warehouse` 버킷 생성

또는 MinIO Client 사용:
```bash
docker exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123
docker exec minio mc mb local/warehouse
```

#### Step 6: Python 의존성 설치

```bash
# 센서 데이터 생성기
cd generator
poetry install

# PySpark Job
cd ../spark-jobs/pyspark-jobs
poetry install

# FastAPI 서버
cd ../../../spark-fastapi
poetry install
```

#### Step 7: 프론트엔드 의존성 설치

```bash
cd ../spark-fastapi-ui
npm install
```

### 4.5 첫 실행 체크리스트

- [ ] Docker 컨테이너 8개 모두 `Up` 상태
- [ ] Kafka UI (http://localhost:9090) 접속 가능
- [ ] Spark Master UI (http://localhost:8080) 접속 가능
- [ ] MinIO Console (http://localhost:9001) 접속 및 `warehouse` 버킷 존재
- [ ] PostgreSQL 연결 확인:
  ```bash
  docker exec -it postgresql psql -U etl_user -d etl_db -c "\dt"
  ```
- [ ] Kafka `sensor-raw` 토픽 존재

---

## 5. 시스템 운영

### 5.1 시스템 시작 순서

**전체 시작**:
```bash
cd etl-cluster

# 1. 데이터베이스 및 스토리지
docker compose -f docker-compose-postgresql.yaml up -d
docker compose -f docker-compose-minio.yaml up -d

# 2. 메시지 브로커
docker compose -f docker-compose-kafka.yaml up -d

# 3. 처리 엔진
docker compose -f docker-compose-spark.yaml up -d

# 4. 웹 서버 (선택)
cd ../spark-fastapi
./startFastApi.sh  # 백그라운드에서 실행

cd ../spark-fastapi-ui
npm run dev
```

### 5.2 시스템 종료 순서

**🚀 자동 종료 (권장)**:
```bash
cd ${HOME}/etl-cluster-test
./scripts/teardown.sh
```

이 스크립트는:
- 모든 Docker 컨테이너 종료
- 선택적으로 볼륨 삭제 (y/N 프롬프트)

**📋 수동 종료** (역순):
```bash
# 1. 웹 서버 종료 (Ctrl+C)

# 2. 처리 엔진 종료
cd etl-cluster
docker compose -f docker-compose-spark.yaml down

# 3. 메시지 브로커 종료
docker compose -f docker-compose-kafka.yaml down

# 4. 데이터베이스 및 스토리지 종료
docker compose -f docker-compose-minio.yaml down
docker compose -f docker-compose-postgresql.yaml down
```

**데이터 완전 삭제** (주의):
```bash
# 볼륨 삭제 (Kafka 데이터 손실)
docker volume rm kafka-data-1 kafka-secrets-1 kafka-config-1

# 네트워크 삭제
docker network rm etl-network
```

### 5.3 모니터링 대시보드

| 대시보드 | URL | 로그인 정보 |
|---------|-----|------------|
| Kafka UI | http://localhost:9090 | 불필요 |
| Spark Master UI | http://localhost:8080 | 불필요 |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| pgAdmin | http://localhost:5050 | admin@admin.com / admin |
| FastAPI Docs | http://localhost:8000/docs | 불필요 |
| spark-fastapi-ui | http://localhost:5173 | 불필요 |

### 5.4 로그 확인

#### Docker 컨테이너 로그
```bash
# 전체 로그 스트리밍
docker logs -f kafka-broker-1
docker logs -f spark-master
docker logs -f spark-worker-1

# 최근 100줄 확인
docker logs --tail 100 postgresql
```

#### Spark Job 로그
```bash
# PySpark Job 실행 로그
tail -f iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.log
```

#### FastAPI 서버 로그
```bash
# 서버 실행 터미널에서 실시간 확인
# 또는 백그라운드 실행 시
tail -f spark-fastapi/nohup.out
```

---

## 6. 데이터 파이프라인 실행

### 6.1 센서 데이터 생성

```bash
cd iot-pipeline/generator
poetry run python sensor_producer.py
```

**실행 결과**:
```
Sent: {'sensor_id': 'TEMP-001', 'sensor_type': 'temperature', ...}
Sent: {'sensor_id': 'HUMID-001', 'sensor_type': 'humidity', ...}
Sent: {'sensor_id': 'PRESS-001', 'sensor_type': 'pressure', ...}
```

**검증 - Kafka UI**:
1. http://localhost:9090 접속
2. Topics → sensor-raw 클릭
3. Messages 탭에서 실시간 메시지 확인

**검증 - Kafka CLI**:
```bash
docker exec kafka-broker-1 /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka-broker-1:29092 \
  --topic sensor-raw \
  --from-beginning \
  --max-messages 5
```

### 6.2 Spark 배치 처리 Job 실행

#### 로컬 모드 실행 (권장 - 디버깅 쉬움)

```bash
cd iot-pipeline/spark-jobs/pyspark-jobs
spark-submit --master local[*] batch_aggregation.py
```

#### 클러스터 모드 실행

```bash
spark-submit \
  --master spark://localhost:7077 \
  --deploy-mode client \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.hadoop:hadoop-aws:3.3.4,software.amazon.awssdk:bundle:2.21.42,org.postgresql:postgresql:42.7.3 \
  batch_aggregation.py
```

**주요 패키지 설명**:
- `iceberg-spark-runtime`: Iceberg 테이블 읽기/쓰기
- `spark-sql-kafka`: Kafka 데이터 소스
- `hadoop-aws`: S3A 파일 시스템 (MinIO)
- `postgresql`: JDBC 드라이버

**실행 로그 확인**:
```bash
tail -f batch_aggregation.log
```

**Spark UI에서 확인**:
1. http://localhost:8080 접속
2. Running Applications 또는 Completed Applications 확인
3. Application UI 클릭 → Jobs, Stages, Storage 탭 확인

### 6.3 Iceberg 테이블 조회

#### spark-sql CLI 실행

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

#### SQL 쿼리 예제

```sql
-- 네임스페이스(스키마) 목록
SHOW NAMESPACES IN iceberg;

-- 테이블 목록
SHOW TABLES IN iceberg.iot;

-- 데이터 조회
SELECT * FROM iceberg.iot.hourly_stats
ORDER BY hour DESC
LIMIT 10;

-- 특정 센서 타입 집계
SELECT
  hour,
  sensor_type,
  location,
  avg_value,
  min_value,
  max_value,
  count
FROM iceberg.iot.hourly_stats
WHERE sensor_type = 'temperature'
ORDER BY hour DESC;

-- 테이블 스냅샷 이력 (Time Travel)
SELECT * FROM iceberg.iot.hourly_stats.snapshots;

-- 테이블 삭제 (데이터 완전 삭제)
DROP TABLE IF EXISTS iceberg.iot.hourly_stats PURGE;
```

#### PostgreSQL에서 메타데이터 확인

```bash
docker exec -it postgresql psql -U etl_user -d etl_db
```

```sql
-- Iceberg 카탈로그 테이블
\dt iceberg.*

-- 테이블 메타데이터
SELECT * FROM iceberg.iceberg_tables;

-- 스냅샷 정보
SELECT * FROM iceberg.iceberg_namespace_properties;
```

---

## 7. API 서버 사용

### 7.1 FastAPI 서버 실행

```bash
cd spark-fastapi

# 방법 1: 시작 스크립트 사용
./startFastApi.sh

# 방법 2: 직접 실행
poetry run python -m app.main

# 방법 3: Uvicorn 직접 실행
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**실행 확인**:
```bash
curl http://localhost:8000/api/v1/cluster/status
```

### 7.2 주요 API 엔드포인트

#### 📌 클러스터 모니터링

**GET /api/v1/cluster/status** - 클러스터 상태
```bash
curl http://localhost:8000/api/v1/cluster/status | jq
```

응답 예시:
```json
{
  "status": "ALIVE",
  "total_cores": 8,
  "used_cores": 0,
  "total_memory": 4096,
  "used_memory": 0,
  "worker_count": 1,
  "active_app_count": 0
}
```

**GET /api/v1/cluster/workers** - Worker 정보
```bash
curl http://localhost:8000/api/v1/cluster/workers | jq
```

응답 예시:
```json
[
  {
    "id": "worker-20241211000000-172.18.0.5-8881",
    "host": "172.18.0.5",
    "port": 8881,
    "cores": 8,
    "memory": 4096,
    "state": "ALIVE"
  }
]
```

#### 📌 애플리케이션 관리

**GET /api/v1/jobs/apps** - 애플리케이션 목록
```bash
# 실행 중인 앱만
curl http://localhost:8000/api/v1/jobs/apps | jq

# 완료된 앱 포함
curl "http://localhost:8000/api/v1/jobs/apps?include_completed=true" | jq
```

**GET /api/v1/jobs/apps/{app_id}** - 특정 앱 조회
```bash
curl http://localhost:8000/api/v1/jobs/apps/app-20241211000001-0001 | jq
```

**DELETE /api/v1/jobs/apps/{app_id}** - 앱 종료
```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/apps/app-20241211000001-0001 | jq
```

응답 예시:
```json
{
  "success": true,
  "message": "Application app-20241211000001-0001 killed successfully"
}
```

#### 📌 Job 제출

**POST /api/v1/jobs/submit** - Spark Job 제출
```bash
curl -X POST http://localhost:8000/api/v1/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "script_path": "${HOME}/etl-cluster-test/iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.py",
    "driver_memory": "2g",
    "executor_memory": "2g",
    "executor_cores": 2,
    "num_executors": 1
  }' | jq
```

응답 예시:
```json
{
  "success": true,
  "message": "Spark job submitted with PID: 12345"
}
```

### 7.3 Swagger UI 사용

1. http://localhost:8000/docs 접속
2. 각 엔드포인트 확장
3. "Try it out" 버튼 클릭
4. 파라미터 입력 후 "Execute" 실행
5. 응답 확인

### 7.4 웹 UI 실행

```bash
cd spark-fastapi-ui
npm run dev
```

브라우저에서 http://localhost:5173 접속

**주요 페이지**:
- **Cluster Overview**: 클러스터 상태, Worker 목록
- **Applications**: 실행 중/완료된 애플리케이션
- **Submit Job**: 새로운 Spark Job 제출

---

## 8. 확장 및 커스터마이징

### 8.1 새로운 센서 타입 추가

#### Step 1: 센서 데이터 생성기 수정

`iot-pipeline/generator/sensor_producer.py`:

```python
# SENSOR_CONFIGS에 새 센서 타입 추가
SENSOR_CONFIGS = {
    "temperature": {...},
    "humidity": {...},
    "pressure": {...},
    "vibration": {  # 새로운 센서 타입
        "sensors": ["VIB-001", "VIB-002"],
        "unit": "mm/s",
        "min_value": 0.0,
        "max_value": 50.0,
        "threshold_min": 0.0,
        "threshold_max": 30.0
    }
}
```

#### Step 2: Spark 집계 로직 확인

`iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.py`는 센서 타입에 무관하게 동작하므로 수정 불필요.

#### Step 3: 테스트

```bash
cd generator
poetry run python sensor_producer.py
```

Kafka UI에서 `vibration` 타입 메시지 확인.

### 8.2 집계 주기 변경 (시간별 → 분별)

`batch_aggregation.py` 수정:

```python
# 기존: hourly aggregation
df_aggregated = df_with_hour.groupBy("hour", "sensor_type", "location")

# 변경: minutely aggregation
df_with_minute = df.withColumn(
    "minute",
    date_format(col("timestamp"), "yyyy-MM-dd HH:mm")
)
df_aggregated = df_with_minute.groupBy("minute", "sensor_type", "location")
```

테이블 이름도 `hourly_stats` → `minutely_stats`로 변경.

### 8.3 새로운 API 엔드포인트 추가

#### Step 1: Schema 정의

`spark-fastapi/app/schemas/cluster.py`:

```python
class CustomMetric(BaseModel):
    metric_name: str
    value: float
```

#### Step 2: Endpoint 구현

`spark-fastapi/app/api/endpoints/cluster.py`:

```python
@router.get("/metrics", response_model=list[CustomMetric])
async def get_custom_metrics():
    # Spark Master API 또는 PostgreSQL 쿼리
    return [...]
```

#### Step 3: 테스트 작성

`spark-fastapi/tests/integration/test_cluster_endpoints.py`:

```python
def test_get_custom_metrics(test_client):
    response = test_client.get("/api/v1/cluster/metrics")
    assert response.status_code == 200
```

### 8.4 테스트 실행

#### 단위 테스트

```bash
cd spark-fastapi
poetry run pytest tests/unit/ -v
```

#### 통합 테스트

```bash
poetry run pytest tests/integration/ -v
```

#### 커버리지 확인

```bash
poetry run pytest --cov=app --cov-report=html
firefox htmlcov/index.html  # 브라우저에서 열기
```

**참고**: respx 모킹 이슈로 일부 테스트가 skip됩니다 (`@pytest.mark.respx_issue`).

---

## 9. 트러블슈팅

### 9.1 Kafka 연결 실패

**증상**:
```
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
```

**해결**:
1. Kafka 컨테이너 실행 확인:
   ```bash
   docker ps | grep kafka
   ```
2. 네트워크 확인:
   ```bash
   docker network inspect etl-network
   ```
3. /etc/hosts에 `127.0.0.1 kafka-broker-1` 추가

### 9.2 Spark Master 연결 실패

**증상**:
```
Exception: Could not connect to Spark Master at spark://localhost:7077
```

**해결**:
1. Spark Master 컨테이너 실행 확인
2. Spark Master UI (http://localhost:8080) 접속 가능한지 확인
3. 포트 7077 사용 중인지 확인:
   ```bash
   lsof -i :7077
   ```

### 9.3 MinIO S3 접근 실패

**증상**:
```
org.apache.hadoop.fs.s3a.AWSClientIOException: doesBucketExistV2 on warehouse
```

**해결**:
1. MinIO 컨테이너 실행 확인
2. MinIO Console에서 `warehouse` 버킷 존재 확인
3. Access Key/Secret Key 확인:
   ```bash
   docker logs minio | grep minioadmin
   ```

### 9.4 PostgreSQL JDBC 연결 실패

**증상**:
```
org.postgresql.util.PSQLException: Connection refused
```

**해결**:
1. PostgreSQL 컨테이너 실행 확인
2. JDBC URL 확인: `jdbc:postgresql://postgresql:5432/etl_db`
3. 계정 정보 확인: `etl_user` / `etl_password`
4. 초기화 SQL 실행 여부 확인:
   ```bash
   docker exec -it postgresql psql -U etl_user -d etl_db -c "\dt iceberg.*"
   ```

### 9.5 Iceberg 테이블이 보이지 않음

**증상**:
```
Table iot.hourly_stats not found
```

**해결**:
1. Spark Job이 정상 실행되었는지 확인 (로그 확인)
2. PostgreSQL에서 메타데이터 확인:
   ```sql
   SELECT * FROM iceberg.iceberg_tables;
   ```
3. MinIO에서 Parquet 파일 확인 (MinIO Console → warehouse 버킷)

### 9.6 FastAPI 서버 CORS 에러

**증상** (브라우저 콘솔):
```
Access to fetch at 'http://localhost:8000/api/v1/cluster/status' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**해결**:
1. `spark-fastapi/app/main.py`에서 CORS 설정 확인:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. FastAPI 서버 재시작

### 9.7 Docker 디스크 공간 부족

**증상**:
```
Error response from daemon: no space left on device
```

**해결**:
```bash
# 사용하지 않는 컨테이너, 이미지, 볼륨 삭제
docker system prune -a --volumes

# 특정 볼륨만 삭제
docker volume ls
docker volume rm <volume_name>
```

### 9.8 Kafka 메시지가 소비되지 않음

**증상**: Spark Job을 실행해도 데이터가 읽히지 않음

**해결**:
1. Kafka 토픽에 메시지가 있는지 확인:
   ```bash
   docker exec kafka-broker-1 /opt/kafka/bin/kafka-console-consumer.sh \
     --bootstrap-server kafka-broker-1:29092 \
     --topic sensor-raw \
     --from-beginning \
     --max-messages 1
   ```
2. Consumer Group 확인:
   ```bash
   docker exec kafka-broker-1 /opt/kafka/bin/kafka-consumer-groups.sh \
     --bootstrap-server kafka-broker-1:29092 \
     --list
   ```
3. Offset 리셋:
   ```bash
   docker exec kafka-broker-1 /opt/kafka/bin/kafka-consumer-groups.sh \
     --bootstrap-server kafka-broker-1:29092 \
     --group spark-kafka-consumer \
     --reset-offsets --to-earliest --execute --topic sensor-raw
   ```

---

## 10. 기술 스택 상세

### 10.1 주요 기술 및 버전

| 기술 | 버전 | 목적 | 선택 이유 |
|-----|------|------|----------|
| **Apache Kafka** | 3.9.1 | 메시지 브로커 | KRaft 모드로 Zookeeper 불필요, 높은 처리량 |
| **Apache Spark** | 3.5.3 | 분산 데이터 처리 | 인메모리 처리로 빠른 배치 집계 |
| **Apache Iceberg** | 1.5.2 | 테이블 포맷 | 스키마 진화, ACID 트랜잭션 지원 |
| **PostgreSQL** | 15 | 메타데이터 카탈로그 | Iceberg JDBC 카탈로그 저장 |
| **MinIO** | latest | 객체 스토리지 | S3 호환 로컬 스토리지 |
| **FastAPI** | 0.123.5 | REST API 프레임워크 | 빠른 성능, 자동 API 문서 생성 |
| **React** | 18 | 프론트엔드 UI | 컴포넌트 기반, 풍부한 생태계 |
| **Python** | 3.11+ | 데이터 처리 스크립트 | PySpark, Kafka Producer |
| **TypeScript** | 5.x | 프론트엔드 타입 안정성 | 런타임 에러 방지 |

### 10.2 의존성 관리

#### Python (Poetry)

```bash
# 새 패키지 추가
poetry add <package_name>

# 개발 의존성 추가
poetry add --group dev <package_name>

# 의존성 업데이트
poetry update

# 가상환경 활성화
poetry shell
```

#### Node.js (npm)

```bash
# 새 패키지 추가
npm install <package_name>

# 개발 의존성 추가
npm install --save-dev <package_name>

# 의존성 업데이트
npm update
```

#### Spark (Maven Packages)

```bash
# spark-submit 시 --packages 옵션 사용
spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2
```

### 10.3 네트워크 아키텍처

**Docker 브릿지 네트워크 (`etl-network`)**:

- 모든 컨테이너는 같은 네트워크에 연결
- 컨테이너 이름으로 통신 (예: `kafka-broker-1:29092`)
- 호스트에서는 `localhost:<포트>`로 접근

**포트 매핑**:

```yaml
# docker compose 예시
ports:
  - "9092:9092"   # 호스트:컨테이너
```

---

## 11. 참고 자료

### 11.1 공식 문서

- **Apache Kafka**: https://kafka.apache.org/documentation/
- **Apache Spark**: https://spark.apache.org/docs/latest/
- **Apache Iceberg**: https://iceberg.apache.org/docs/latest/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Poetry**: https://python-poetry.org/docs/
- **MinIO**: https://min.io/docs/minio/linux/index.html
- **PostgreSQL**: https://www.postgresql.org/docs/

### 11.2 프로젝트 내부 문서

- **TESTING.md**: 테스트 전략 및 실행 가이드
- **iot-pipeline/README.md**: 데이터 파이프라인 상세 가이드
- **spark-fastapi/README.md**: API 서버 상세 문서
- **spark-fastapi-ui/README.md**: 프론트엔드 개발 가이드

### 11.3 주요 학습 자료

- **Kafka 기초**: https://kafka.apache.org/quickstart
- **Spark Structured Streaming**: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
- **Iceberg 시작하기**: https://iceberg.apache.org/docs/latest/getting-started/
- **FastAPI 튜토리얼**: https://fastapi.tiangolo.com/tutorial/

### 11.4 커뮤니티 및 지원

- **Stack Overflow**: `apache-kafka`, `apache-spark`, `apache-iceberg`, `fastapi` 태그
- **GitHub Issues**:
  - Kafka: https://github.com/apache/kafka/issues
  - Spark: https://github.com/apache/spark/issues
  - Iceberg: https://github.com/apache/iceberg/issues
  - FastAPI: https://github.com/tiangolo/fastapi/issues

---

## 📌 체크리스트 (인수인계 완료 확인)

- [ ] Docker 환경 구축 완료 (모든 컨테이너 실행)
- [ ] Kafka 토픽 생성 및 메시지 확인
- [ ] Spark 배치 Job 실행 성공
- [ ] Iceberg 테이블 조회 가능
- [ ] FastAPI 서버 실행 및 API 호출 성공
- [ ] 웹 UI 접속 및 클러스터 모니터링 확인
- [ ] 각 서비스 로그 확인 방법 숙지
- [ ] 트러블슈팅 가이드 숙지
- [ ] 테스트 실행 및 커버리지 확인

---

## 🔗 연락처

**질문 또는 이슈 발생 시**:
- 프로젝트 GitHub Repository: (URL 추가 필요)
- 담당자 이메일: (이메일 추가 필요)

**최종 업데이트**: 2025-12-11
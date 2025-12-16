# Spark FastAPI 설계 문서

## 개요

Spark Standalone 클러스터의 모니터링 및 PySpark Job 제출을 위한 REST API

## 기술 스택

- FastAPI + Pydantic
- httpx (비동기 HTTP 클라이언트, 모니터링용)
- spark-submit CLI (Job 제출용)
- Poetry (패키지 관리)

## 프로젝트 구조

```
spark-fastapi/
├── pyproject.toml
├── .env
└── app/
    ├── main.py
    ├── core/
    │   └── config.py
    ├── api/
    │   ├── router.py
    │   └── endpoints/
    │       ├── cluster.py
    │       └── jobs.py
    ├── schemas/
    │   ├── cluster.py
    │   └── job.py
    └── services/
        └── spark_client.py
```

## API 엔드포인트

### 클러스터 모니터링 (`/api/v1/cluster`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/status` | Spark 클러스터 전체 상태 |
| GET | `/workers` | Spark Worker 목록 및 상태 |


### Job 관리 (`/api/v1/jobs`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/submit` | PySpark 스크립트 제출 |
| GET | `/apps` | 실행 중/완료된 앱 목록 |
| DELETE | `/apps/{app_id}` | 특정 앱 작업 중지 |

## 데이터 스키마

### 클러스터 관련

```python
ClusterStatus:
  status: str
  total_cores: int
  used_cores: int
  total_memory: int
  used_memory: int
  worker_count: int
  active_app_count: int

WorkerInfo:
  id: str
  host: str
  port: int
  cores: int
  memory: int
  state: str

AppInfo:
  id: str
  name: str
  state: str
  cores: int
  memory_per_executor: int
  submitted_time: int      # timestamp (milliseconds)
```

### Job 관련

```python
JobSubmitRequest:
  script_path: str        # uploads 폴더 내 스크립트 파일명 (예: "my_job.py")
  app_args: list[str] = []
  driver_memory: str = "1g"
  executor_memory: str = "1g"
  executor_cores: int = 1
  num_executors: int | None = None

JobSubmitResponse:
  success: bool
  message: str
```

## Spark 연동

### 모니터링 (httpx)

```
GET http://{master}:8080/json/
```

### Job 제출 (spark-submit CLI)

```bash
$SPARK_HOME/bin/spark-submit \
  --master spark://localhost:7077 \
  --deploy-mode client \
  --driver-memory 1g \
  --executor-memory 1g \
  --executor-cores 1 \
  /path/to/script.py
```

- `deploy-mode: client` - Driver가 API 서버(호스트)에서 실행
- **주의**: Standalone 클러스터에서 Python 스크립트는 `client` 모드만 지원 (`cluster` 모드 불가)
- 참고 : https://spark.apache.org/docs/3.5.3/submitting-applications.html

### 설정 (.env)

```
SPARK_MASTER_URL=http://localhost:8080
SPARK_SUBMIT_MASTER=spark://localhost:7077
SPARK_HOME=${HOME}/spark
```

## Spark 클러스터 (Docker)

### 구성

- spark-master: Master (포트 8080, 7077)
- spark-worker-1: Worker 노드 (2코어, 2GB)

## 에러 처리

### HTTP 응답 코드

| 코드 | 상황 |
|------|------|
| 200 | 정상 조회/처리 |
| 400 | 잘못된 요청 또는 Job 실행 실패 |
| 404 | 스크립트 파일 없음 |
| 503 | Spark 클러스터 연결 실패 |

### 에러 응답 형식

```python
ErrorResponse:
  detail: str
```

# Spark FastAPI

Apache Spark 클러스터 모니터링 및 작업 제출을 위한 FastAPI 기반 REST API 서버입니다.

## 개요

이 프로젝트는 다음 기능을 제공하는 RESTful API 인터페이스입니다:
- **클러스터 모니터링**: 실시간 상태, 워커 정보, 애플리케이션 추적
- **작업 관리**: Spark 작업 제출 및 실행 중인 애플리케이션 종료
- **통합**: Apache Spark Standalone 클러스터와 연동

## 주요 기능

- 실시간 클러스터 상태 모니터링 (코어, 메모리, 워커)
- 워커 노드 정보 조회
- 실행 중 및 완료된 애플리케이션 추적
- REST API를 통한 Spark 작업 제출
- 실행 중인 Spark 애플리케이션 종료
- 프론트엔드 통합을 위한 CORS 지원
- 포괄적인 테스트 커버리지 (unit, integration, e2e)

## 기술 스택

- **프레임워크**: FastAPI 0.123.5
- **HTTP 클라이언트**: httpx 0.28.1
- **유효성 검사**: Pydantic 2.12.5
- **설정 관리**: pydantic-settings 2.12.0
- **서버**: Uvicorn (standard extras 포함)
- **테스팅**: pytest, pytest-asyncio, pytest-cov, pytest-mock, respx

## 프로젝트 구조

```
spark-fastapi/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── cluster.py      # 클러스터 모니터링 엔드포인트
│   │   │   └── jobs.py         # 작업 관리 엔드포인트
│   │   └── router.py           # API 라우터 설정
│   ├── core/
│   │   └── config.py           # 애플리케이션 설정
│   ├── schemas/
│   │   ├── cluster.py          # 클러스터 데이터 모델
│   │   └── job.py              # 작업 데이터 모델
│   ├── services/
│   │   └── spark_client.py     # Spark Master API 클라이언트
│   └── main.py                 # FastAPI 애플리케이션 진입점
├── tests/
│   ├── unit/                   # 단위 테스트
│   ├── integration/            # 통합 테스트
│   └── e2e/                    # E2E 테스트
├── pyproject.toml              # Poetry 의존성 관리
├── pytest.ini                  # Pytest 설정
└── startFastApi.sh             # 서버 시작 스크립트
```

## 설치

### 사전 요구사항

- Python 3.11 이상
- Poetry
- Apache Spark (설정 및 실행 중)

### 설정

1. 의존성 설치:
```bash
poetry install
```

2. `.env` 파일에 환경 변수 설정:
```env
SPARK_MASTER_URL=http://localhost:8080
SPARK_SUBMIT_MASTER=spark://localhost:7077
SPARK_HOME=/path/to/spark
```

## 사용법

### API 서버 시작

시작 스크립트 사용:
```bash
./startFastApi.sh
```

또는 직접 실행:
```bash
poetry run python -m app.main
```

API는 `http://localhost:8000`에서 접근 가능합니다.

### API 문서

대화형 API 문서:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API 엔드포인트

### 클러스터 모니터링

#### 클러스터 상태 조회
```http
GET /api/v1/cluster/status
```

응답:
```json
{
  "status": "ALIVE",
  "total_cores": 8,
  "used_cores": 4,
  "total_memory": 8192,
  "used_memory": 2048,
  "worker_count": 2,
  "active_app_count": 1
}
```

#### 워커 목록 조회
```http
GET /api/v1/cluster/workers
```

응답:
```json
[
  {
    "id": "worker-20231210120000-192.168.1.100-7078",
    "host": "192.168.1.100",
    "port": 7078,
    "cores": 4,
    "memory": 4096,
    "state": "ALIVE"
  }
]
```

#### 애플리케이션 목록 조회
```http
GET /api/v1/jobs/apps?include_completed=false
```

응답:
```json
[
  {
    "id": "app-20231210120000-0001",
    "name": "MySparkApp",
    "state": "RUNNING",
    "cores": 2,
    "memory_per_executor": 1024,
    "submitted_time": 1702195200000
  }
]
```

#### 애플리케이션 ID로 조회
```http
GET /api/v1/jobs/apps/{app_id}
```

### 작업 관리

#### 작업 제출
```http
POST /api/v1/jobs/submit
Content-Type: application/json

{
  "script_path": "/path/to/script.py",
  "driver_memory": "1g",
  "executor_memory": "2g",
  "executor_cores": 2,
  "num_executors": 2
}
```

응답:
```json
{
  "success": true,
  "message": "Job submitted (PID: 12345)"
}
```

#### 작업 종료
```http
DELETE /api/v1/jobs/apps/{app_id}
```

응답:
```json
{
  "success": true,
  "message": "Application app-20231210120000-0001 killed successfully"
}
```

## 설정

### 설정 항목 (app/core/config.py)

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `app_name` | "Spark Cluster API" | 애플리케이션 이름 |
| `debug` | `false` | 디버그 모드 |
| `spark_master_url` | `http://localhost:8080` | Spark Master Web UI URL |
| `spark_submit_master` | `spark://localhost:7077` | 작업 제출용 Spark Master URL |
| `spark_home` | `${HOME}/spark` | Spark 설치 디렉토리 |

### CORS 설정

기본 허용 origin: `http://localhost:5173`

CORS 설정 수정을 원할 경우 `app/main.py` 파일 수정:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 여기를 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 테스트

전체 테스트 실행:
```bash
poetry run pytest
```

커버리지 포함 실행:
```bash
poetry run pytest --cov=app --cov-report=html
```

특정 테스트 유형 실행:
```bash
# 단위 테스트만
poetry run pytest tests/unit/

# 통합 테스트만
poetry run pytest tests/integration/

# E2E 테스트만
poetry run pytest tests/e2e/
```

상세한 테스트 문서는 [tests/README.md](tests/README.md)를 참조하세요.

## 개발

### 코드 구조

- **API 계층** (`app/api/`): FastAPI 라우트 및 엔드포인트
- **서비스 계층** (`app/services/`): 비즈니스 로직 및 외부 API 클라이언트
- **스키마 계층** (`app/schemas/`): 요청/응답 유효성 검사를 위한 Pydantic 모델
- **코어** (`app/core/`): 애플리케이션 설정

### 새 엔드포인트 추가

1. `app/schemas/`에 스키마 정의
2. `app/services/`에 서비스 로직 구현
3. `app/api/endpoints/`에 엔드포인트 생성
4. `tests/`에 테스트 추가

## 프론트엔드 통합

이 API는 `spark-fastapi-ui` React 프론트엔드와 함께 작동하도록 설계되었습니다. CORS 설정은 `http://localhost:5173` (Vite 기본 포트)에서의 요청을 허용합니다.

## Spark 패키지

작업 제출 시 자동으로 포함되는 Spark 패키지:
- `org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2`
- `org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3`
- `org.apache.hadoop:hadoop-aws:3.3.4`
- `software.amazon.awssdk:bundle:2.21.42`
- `org.postgresql:postgresql:42.7.3`

## 에러 처리

모든 엔드포인트는 적절한 HTTP 상태 코드를 반환합니다:
- `200`: 성공
- `400`: 잘못된 요청 (유효하지 않은 파라미터)
- `404`: 리소스를 찾을 수 없음
- `503`: 서비스 사용 불가 (Spark 클러스터 연결 실패)

## 라이선스

MIT

## 작성자

hkkim
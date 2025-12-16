# Spark FastAPI 프로젝트 테스트 가이드

이 문서는 백엔드(spark-fastapi)와 프론트엔드(spark-fastapi-ui) 컴포넌트에 대한 테스트 전략 개요를 제공합니다.

## 개요

프로젝트는 3가지 테스트 레벨로 구성된 포괄적인 테스트 전략을 사용합니다:

1. **Unit Tests** - 개별 함수/컴포넌트에 대한 빠르고 격리된 테스트
2. **Integration Tests** - API 엔드포인트 및 컴포넌트 상호작용 테스트
3. **E2E Tests** - 실제 사용자 시나리오를 시뮬레이션하는 전체 워크플로우 테스트

## 백엔드 테스트 (spark-fastapi)

**프레임워크**: pytest + pytest-asyncio + respx

### 설정

```bash
cd spark-fastapi
poetry install --with dev
```

### 테스트 실행

```bash
# 전체 테스트 (기본적으로 E2E 제외)
poetry run pytest

# 단위 테스트만
poetry run pytest tests/unit/

# 통합 테스트만
poetry run pytest tests/integration/

# E2E 테스트 (실행 중인 Spark 클러스터 필요)
poetry run pytest tests/e2e/

# 커버리지 포함
poetry run pytest --cov=app --cov-report=html
```

### 테스트 구조

```
tests/
├── conftest.py                              # 공유 fixture
├── unit/
│   ├── test_spark_client.py               # SparkClient 서비스 테스트
│   ├── test_schemas.py                    # Pydantic 스키마 테스트
│   └── test_config.py                     # 설정 테스트
├── integration/
│   ├── test_cluster_endpoints.py          # 클러스터 API 엔드포인트 테스트
│   ├── test_jobs_endpoints.py             # 작업 API 엔드포인트 테스트
│   ├── test_app_endpoint.py               # 앱 조회 엔드포인트 테스트
│   └── test_error_cases.py                # 에러 케이스 테스트
└── e2e/
    └── test_real_spark_cluster.py         # 실제 Spark 클러스터 테스트
```

### 테스트된 주요 기능

- ✅ 클러스터 상태 조회
- ✅ 워커 정보
- ✅ 애플리케이션 목록 조회 (완료된 앱 포함/미포함)
- ✅ 작업 제출 유효성 검사
- ✅ 작업 종료 (DELETE /jobs/{app_id})
- ✅ 에러 처리 및 유효성 검사
- ✅ HTTP 상태 코드
- ✅ Pydantic 스키마 검증
- ✅ 설정 관리

상세 내용은 [spark-fastapi/tests/README.md](spark-fastapi/tests/README.md)를 참조하세요.


## 전체 테스트 스위트 실행

### 사전 요구사항

1. Spark 클러스터 시작:
```bash
docker compose -f docker-compose-spark.yaml up -d
```

2. 백엔드 API 시작:
```bash
cd spark-fastapi
poetry run uvicorn app.main:app --reload
```

### 모든 테스트 실행

```bash
# 백엔드 테스트
cd spark-fastapi
poetry run pytest                           # Unit + Integration
SKIP_E2E=0 poetry run pytest tests/e2e/    # E2E (Spark 클러스터 필요)

```

## 테스트 커버리지 목표

### 백엔드
- **Unit Tests**: SparkClient 메서드, 유틸리티 함수, 스키마, 설정
- **Integration Tests**: 모든 API 엔드포인트 (모킹된 Spark Master 사용)
- **E2E Tests**: Docker Spark 클러스터를 사용한 실제 작업 제출 및 종료


## CI/CD 파이프라인 예시

```yaml
# .github/workflows/test.yml 예시
name: Test

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        working-directory: ./spark-fastapi
        run: poetry install --with dev
      - name: Run unit tests
        working-directory: ./spark-fastapi
        run: poetry run pytest tests/unit/ -v
      - name: Run integration tests
        working-directory: ./spark-fastapi
        run: poetry run pytest tests/integration/ -v
```

## 테스트 개발 워크플로우

### 새로운 백엔드 엔드포인트 추가

1. 서비스 레이어에 대한 단위 테스트 작성 (`tests/unit/`)
2. 엔드포인트에 대한 통합 테스트 작성 (`tests/integration/`)
3. 중요한 워크플로우에 대해 선택적으로 E2E 테스트 추가 (`tests/e2e/`)
4. 테스트 실행: `poetry run pytest`

## 일반적인 테스트 패턴

### 백엔드: HTTP 요청 모킹

```python
@respx.mock
async def test_endpoint(test_client):
    respx.get("http://localhost:8080/json/").mock(
        return_value=httpx.Response(200, json={"status": "ALIVE"})
    )
    response = test_client.get("/api/v1/cluster/status")
    assert response.status_code == 200
```

## 디버깅 팁

### 백엔드
- 상세 출력을 위해 `-v` 플래그 사용: `pytest -v`
- print 문을 보려면 `-s` 사용: `pytest -s`
- 단일 테스트 실행: `pytest tests/unit/test_file.py::test_function`

## 리소스

- [pytest 문서](https://docs.pytest.org/)
- [Vitest 문서](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright 문서](https://playwright.dev/)
# Spark FastAPI 테스트

Spark FastAPI 백엔드를 위한 종합 테스트 스위트입니다.

## 테스트 구조

```
tests/
├── conftest.py              # 공유 pytest fixture
├── unit/                    # 단위 테스트 (빠름, 외부 의존성 없음)
│   └── test_spark_client.py
├── integration/             # 통합 테스트 (외부 서비스 모킹)
│   ├── test_cluster_endpoints.py
│   └── test_jobs_endpoints.py
└── e2e/                     # End-to-end 테스트 (실제 Spark 클러스터 필요)
    └── test_real_spark_cluster.py
```

## 테스트 의존성

테스트 의존성 설치:

```bash
poetry install --with dev
```

의존성 목록:
- `pytest` - 테스팅 프레임워크
- `pytest-asyncio` - 비동기 테스트 지원
- `pytest-cov` - 코드 커버리지 리포팅
- `pytest-mock` - 모킹 유틸리티
- `respx` - httpx용 HTTP 모킹

## 테스트 실행

### 전체 테스트 실행 (E2E 제외)
```bash
poetry run pytest
```

### 단위 테스트만 실행
```bash
poetry run pytest tests/unit/
```

### 통합 테스트만 실행
```bash
poetry run pytest tests/integration/
```

### E2E 테스트 실행 (실행 중인 Spark 클러스터 필요)
```bash
# 먼저 Spark 클러스터 시작
cd ${HOME}/etl-cluster-test
docker compose -f docker-compose-spark.yaml up -d

# E2E 테스트 실행
poetry run pytest tests/e2e/

# 또는 E2E 포함 전체 테스트 실행
SKIP_E2E=0 poetry run pytest
```

### 커버리지 리포트와 함께 실행
```bash
poetry run pytest --cov=app --cov-report=html
```

커버리지 리포트 확인:
```bash
open htmlcov/index.html
```

### 특정 테스트 실행
```bash
poetry run pytest tests/unit/test_spark_client.py::TestGetClusterStatus::test_successful_cluster_status
```

### 상세 출력과 함께 실행
```bash
poetry run pytest -v
```

## 테스트 카테고리

### 단위 테스트 (Unit Tests)
- 개별 함수와 메서드를 독립적으로 테스트
- 외부 의존성(HTTP 요청, 파일 시스템 등)은 모킹 사용
- 빠른 실행 (1초 이내 실행되어야 함)

### 통합 테스트 (Integration Tests)
- 모킹된 Spark Master와 함께 API 엔드포인트 테스트
- FastAPI를 통한 요청/응답 흐름 검증
- 에러 핸들링 및 유효성 검사 테스트

### E2E 테스트 (End-to-End Tests)
- 실제 Docker Spark 클러스터에 대해 테스트
- 전체 워크플로우 검증 (작업 제출, 상태 확인, 작업 종료)
- 느린 실행, 외부 서비스 필요
- 기본적으로 스킵됨 (`SKIP_E2E=1` 설정)

## CI/CD 통합

CI/CD 파이프라인에서는 다음 순서로 테스트 실행:

```bash
# 1. 단위 테스트 (빠른 피드백)
poetry run pytest tests/unit/ -v

# 2. 통합 테스트
poetry run pytest tests/integration/ -v

# 3. E2E 테스트 (Spark 클러스터 사용 가능한 경우만)
SKIP_E2E=0 poetry run pytest tests/e2e/ -v
```

## 새 테스트 작성하기

### 단위 테스트 예시
```python
# tests/unit/test_my_service.py
import pytest
from app.services.my_service import MyService

def test_my_function():
    result = MyService.my_function(input_data)
    assert result == expected_output
```

### 통합 테스트 예시
```python
# tests/integration/test_my_endpoint.py
import respx
import httpx

@respx.mock
def test_my_endpoint(test_client):
    respx.get("http://external-api.com").mock(
        return_value=httpx.Response(200, json={"data": "value"})
    )

    response = test_client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
```

## 문제 해결

### 테스트가 멈추거나 타임아웃 발생
- 외부 서비스(Spark 클러스터)가 실행 중인지 확인
- 비동기 테스트의 타임아웃 값 증가
- `pytest -v`로 상세 출력 사용

### Import 에러
- poetry 가상 환경에 있는지 확인: `poetry shell`
- 모든 의존성이 설치되었는지 확인: `poetry install --with dev`

### E2E 테스트 실패
- Docker Spark 클러스터가 실행 중인지 확인: `docker compose -f docker-compose-spark.yaml ps`
- Spark Master UI 확인: http://localhost:8080
- Spark Master로의 네트워크 연결 확인

### 커버리지가 모든 파일을 표시하지 않음
- 프로젝트 루트에서 실행: `cd ${HOME}/etl-cluster-test/spark-fastapi`
- `pytest.ini` 파일이 존재하는지 확인
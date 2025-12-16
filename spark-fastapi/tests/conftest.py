"""Shared pytest fixtures for all tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def mock_spark_master_response():
    """Mock Spark Master JSON response."""
    return {
        "status": "ALIVE",
        "cores": 8,
        "coresused": 2,
        "memory": 16384,
        "memoryused": 4096,
        "workers": [
            {
                "id": "worker-1",
                "host": "localhost",
                "port": 8881,
                "cores": 4,
                "memory": 8192,
                "state": "ALIVE",
            },
            {
                "id": "worker-2",
                "host": "localhost",
                "port": 8882,
                "cores": 4,
                "memory": 8192,
                "state": "ALIVE",
            },
        ],
        "activeapps": [
            {
                "id": "app-20241210000001-0001",
                "name": "Test App 1",
                "cores": 2,
                "memoryperslave": 2048,
                "starttime": 1702123456789,
            }
        ],
        "completedapps": [
            {
                "id": "app-20241210000001-0000",
                "name": "Test App 0",
                "cores": 2,
                "memoryperslave": 2048,
                "starttime": 1702123400000,
            }
        ],
    }


@pytest.fixture
def sample_job_request():
    """Sample job submission request."""
    return {
        "script_path": "/tmp/test_script.py",
        "driver_memory": "1g",
        "executor_memory": "1g",
        "executor_cores": 1,
        "num_executors": None,
    }
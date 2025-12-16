"""Integration tests for cluster endpoints."""
import pytest
import respx
import httpx
from app.core.config import settings


@pytest.fixture
def base_url():
    """Base URL for API endpoints."""
    return "/api/v1/cluster"


@pytest.mark.respx_issue
class TestClusterStatusEndpoint:
    """Tests for GET /api/v1/cluster/status endpoint."""

    @respx.mock
    def test_get_cluster_status_success(self, test_client, base_url, mock_spark_master_response):
        """Test successful cluster status retrieval."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.get(f"{base_url}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ALIVE"
        assert data["total_cores"] == 8
        assert data["used_cores"] == 2
        assert data["worker_count"] == 2
        assert data["active_app_count"] == 1

    @respx.mock
    def test_get_cluster_status_spark_master_error(self, test_client, base_url):
        """Test cluster status with Spark Master error."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )

        response = test_client.get(f"{base_url}/status")

        assert response.status_code == 500


@pytest.mark.respx_issue
class TestWorkersEndpoint:
    """Tests for GET /api/v1/cluster/workers endpoint."""

    @respx.mock
    def test_get_workers_success(self, test_client, base_url, mock_spark_master_response):
        """Test successful workers retrieval."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.get(f"{base_url}/workers")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "worker-1"
        assert data[0]["host"] == "localhost"
        assert data[0]["state"] == "ALIVE"

    @respx.mock
    def test_get_workers_empty(self, test_client, base_url):
        """Test workers endpoint with no workers."""
        response_data = {"workers": []}
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=response_data)
        )

        response = test_client.get(f"{base_url}/workers")

        assert response.status_code == 200
        assert response.json() == []


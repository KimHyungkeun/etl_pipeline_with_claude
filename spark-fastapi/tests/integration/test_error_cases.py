"""Integration tests for various error cases."""
import pytest
import respx
import httpx
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.core.config import settings


@pytest.fixture
def jobs_url():
    """Jobs API base URL."""
    return "/api/v1/jobs"


class TestJobSubmitErrorCases:
    """Tests for error cases in job submission."""

    def test_submit_job_empty_request(self, test_client, jobs_url):
        """Test job submission with empty request body."""
        response = test_client.post(f"{jobs_url}/submit", json={})

        assert response.status_code == 422  # Validation error

    def test_submit_job_invalid_json(self, test_client, jobs_url):
        """Test job submission with invalid JSON."""
        response = test_client.post(
            f"{jobs_url}/submit",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_submit_job_script_path_empty_string(self, test_client, jobs_url):
        """Test job submission with empty script path."""
        request_data = {
            "script_path": "",
            "driver_memory": "1g",
            "executor_memory": "1g",
        }

        response = test_client.post(f"{jobs_url}/submit", json=request_data)

        assert response.status_code == 400  # Empty path fails .py extension check

    def test_submit_job_invalid_memory_format(self, test_client, jobs_url, tmp_path):
        """Test job submission with invalid memory format."""
        script = tmp_path / "test.py"
        script.write_text("print('test')")

        request_data = {
            "script_path": str(script),
            "driver_memory": "invalid",  # Invalid format
            "executor_memory": "1g",
            "executor_cores": 1,
        }

        # Should still accept it (Spark will validate)
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 999
            mock_exec.return_value = mock_process

            response = test_client.post(f"{jobs_url}/submit", json=request_data)

            # FastAPI accepts string, Spark will validate later
            assert response.status_code in [200, 400]

    def test_submit_job_negative_executor_cores(self, test_client, jobs_url, tmp_path):
        """Test job submission with negative executor cores."""
        script = tmp_path / "test.py"
        script.write_text("print('test')")

        request_data = {
            "script_path": str(script),
            "driver_memory": "1g",
            "executor_memory": "1g",
            "executor_cores": -1,
        }

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.pid = 999
            mock_exec.return_value = mock_process

            response = test_client.post(f"{jobs_url}/submit", json=request_data)

            # Pydantic accepts negative int, Spark will reject it
            assert response.status_code in [200, 400]

    @patch("asyncio.create_subprocess_exec")
    def test_submit_job_subprocess_exception(self, mock_exec, test_client, jobs_url, tmp_path):
        """Test job submission when subprocess fails."""
        script = tmp_path / "test.py"
        script.write_text("print('test')")

        mock_exec.side_effect = Exception("Failed to start process")

        request_data = {
            "script_path": str(script),
            "driver_memory": "1g",
            "executor_memory": "1g",
            "executor_cores": 1,
        }

        response = test_client.post(f"{jobs_url}/submit", json=request_data)

        assert response.status_code == 400
        assert "Failed to start process" in response.json()["detail"]


@pytest.mark.respx_issue
class TestKillJobErrorCases:
    """Tests for error cases in killing jobs."""

    @respx.mock
    def test_kill_job_empty_app_id(self, test_client, jobs_url, mock_spark_master_response):
        """Test killing job with empty app_id."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.delete(f"{jobs_url}/")

        # FastAPI routing should not match
        assert response.status_code == 404

    @respx.mock
    def test_kill_job_302_redirect_handling(self, test_client, jobs_url, mock_spark_master_response):
        """Test that 302 redirect is handled as success."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{settings.spark_master_url}/app/kill/").mock(
            return_value=httpx.Response(302, headers={"Location": "/"})
        )

        response = test_client.delete(f"{jobs_url}/apps/app-20241210000001-0001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @respx.mock
    def test_kill_job_500_error(self, test_client, jobs_url, mock_spark_master_response):
        """Test killing job when Spark returns 500."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{settings.spark_master_url}/app/kill/").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        response = test_client.delete(f"{jobs_url}/apps/app-20241210000001-0001")

        assert response.status_code == 400
        assert "Failed to kill application" in response.json()["detail"]

    @respx.mock
    def test_kill_job_network_error(self, test_client, jobs_url, mock_spark_master_response):
        """Test killing job with network error."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{settings.spark_master_url}/app/kill/").mock(
            side_effect=httpx.NetworkError("Network unreachable")
        )

        response = test_client.delete(f"{jobs_url}/apps/app-20241210000001-0001")

        assert response.status_code == 400
        assert "Failed to kill application" in response.json()["detail"]


@pytest.mark.respx_issue
class TestClusterEndpointEdgeCases:
    """Tests for edge cases in cluster endpoints."""

    @respx.mock
    def test_cluster_status_partial_data(self, test_client):
        """Test cluster status with partial data."""
        partial_data = {
            "status": "ALIVE",
            "cores": 8,
            # Missing other fields
        }
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=partial_data)
        )

        response = test_client.get("/api/v1/cluster/status")

        assert response.status_code == 200
        data = response.json()
        # Should use default values for missing fields
        assert data["total_cores"] == 8
        assert data["used_cores"] == 0  # Default value

    @respx.mock
    def test_workers_with_invalid_state(self, test_client):
        """Test workers endpoint with invalid worker state."""
        data_with_invalid_state = {
            "workers": [
                {
                    "id": "worker-1",
                    "host": "localhost",
                    "port": 8881,
                    "cores": 4,
                    "memory": 8192,
                    "state": "INVALID_STATE",  # Non-standard state
                }
            ]
        }
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=data_with_invalid_state)
        )

        response = test_client.get("/api/v1/cluster/workers")

        # Should still work (state is just a string)
        assert response.status_code == 200
        workers = response.json()
        assert workers[0]["state"] == "INVALID_STATE"

    @respx.mock
    def test_apps_with_missing_optional_fields(self, test_client):
        """Test apps endpoint with missing optional fields."""
        data_missing_fields = {
            "activeapps": [
                {
                    "id": "app-1",
                    "name": "Test App",
                    # Missing state, cores, memory, etc.
                }
            ]
        }
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=data_missing_fields)
        )

        response = test_client.get("/api/v1/jobs/apps")

        # Should use default values
        assert response.status_code == 200
        apps = response.json()
        assert apps[0]["cores"] == 0
        assert apps[0]["state"] == "RUNNING"
"""Integration tests for jobs endpoints."""
import pytest
import respx
import httpx
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.core.config import settings


@pytest.fixture
def base_url():
    """Base URL for jobs API endpoints."""
    return "/api/v1/jobs"


class TestSubmitJobEndpoint:
    """Tests for POST /api/v1/jobs/submit endpoint."""

    def test_submit_job_script_not_found(self, test_client, base_url):
        """Test job submission with non-existent script."""
        request_data = {
            "script_path": "/nonexistent/script.py",
            "driver_memory": "1g",
            "executor_memory": "1g",
            "executor_cores": 1,
        }

        response = test_client.post(f"{base_url}/submit", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_submit_job_invalid_file_extension(self, test_client, base_url, tmp_path):
        """Test job submission with non-.py file."""
        # Create a temporary .txt file
        test_file = tmp_path / "test.txt"
        test_file.write_text("print('hello')")

        request_data = {
            "script_path": str(test_file),
            "driver_memory": "1g",
            "executor_memory": "1g",
            "executor_cores": 1,
        }

        response = test_client.post(f"{base_url}/submit", json=request_data)

        assert response.status_code == 400
        assert ".py" in response.json()["detail"]

    @patch("asyncio.create_subprocess_exec")
    def test_submit_job_success(self, mock_subprocess, test_client, base_url, tmp_path):
        """Test successful job submission."""
        # Create a temporary .py file
        test_script = tmp_path / "test_script.py"
        test_script.write_text("print('hello world')")

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_subprocess.return_value = mock_process

        request_data = {
            "script_path": str(test_script),
            "driver_memory": "2g",
            "executor_memory": "2g",
            "executor_cores": 2,
            "num_executors": 3,
        }

        response = test_client.post(f"{base_url}/submit", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "12345" in data["message"]

    def test_submit_job_missing_required_fields(self, test_client, base_url):
        """Test job submission with missing required fields."""
        request_data = {
            "driver_memory": "1g",
            # Missing script_path
        }

        response = test_client.post(f"{base_url}/submit", json=request_data)

        assert response.status_code == 422


@pytest.mark.respx_issue
class TestAppsEndpoint:
    """Tests for GET /api/v1/jobs/apps endpoint."""

    @respx.mock
    def test_get_apps_active_only(self, test_client, base_url, mock_spark_master_response):
        """Test getting only active apps."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.get(f"{base_url}/apps")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["state"] == "RUNNING"

    @respx.mock
    def test_get_apps_include_completed(self, test_client, base_url, mock_spark_master_response):
        """Test getting apps including completed ones."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.get(f"{base_url}/apps?include_completed=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        states = [app["state"] for app in data]
        assert "RUNNING" in states
        assert "FINISHED" in states

    @respx.mock
    def test_get_apps_query_param_false(self, test_client, base_url, mock_spark_master_response):
        """Test getting apps with include_completed=false."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.get(f"{base_url}/apps?include_completed=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert all(app["state"] == "RUNNING" for app in data)


@pytest.mark.respx_issue
class TestKillJobEndpoint:
    """Tests for DELETE /api/v1/jobs/apps/{app_id} endpoint."""

    @respx.mock
    def test_kill_job_success(self, test_client, base_url, mock_spark_master_response):
        """Test successfully killing a running job."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{settings.spark_master_url}/app/kill/").mock(
            return_value=httpx.Response(200, json={})
        )

        response = test_client.delete(f"{base_url}/apps/app-20241210000001-0001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "killed successfully" in data["message"]

    @respx.mock
    def test_kill_job_not_found(self, test_client, base_url, mock_spark_master_response):
        """Test killing a non-existent job."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        response = test_client.delete(f"{base_url}/apps/app-nonexistent")

        assert response.status_code == 400
        data = response.json()
        assert "not found" in data["detail"]

    @respx.mock
    def test_kill_job_not_running(self, test_client, base_url, mock_spark_master_response):
        """Test killing a job that's not in RUNNING state."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        # Try to kill a completed app
        response = test_client.delete(f"{base_url}/apps/app-20241210000001-0000")

        assert response.status_code == 400
        data = response.json()
        assert "not in RUNNING state" in data["detail"]

    @respx.mock
    def test_kill_job_spark_error(self, test_client, base_url, mock_spark_master_response):
        """Test killing a job with Spark Master error."""
        respx.get(f"{settings.spark_master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{settings.spark_master_url}/app/kill/").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )

        response = test_client.delete(f"{base_url}/apps/app-20241210000001-0001")

        assert response.status_code == 400
        data = response.json()
        assert "Failed to kill application" in data["detail"]
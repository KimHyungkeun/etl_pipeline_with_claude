"""Unit tests for SparkClient service."""
import pytest
import respx
import httpx
from app.services.spark_client import SparkClient
from app.schemas.cluster import ClusterStatus, WorkerInfo, AppInfo


@pytest.fixture
def spark_client():
    """Create a SparkClient instance."""
    return SparkClient()


class TestGetClusterStatus:
    """Tests for get_cluster_status method."""

    @respx.mock
    async def test_successful_cluster_status(self, spark_client, mock_spark_master_response):
        """Test successful cluster status retrieval."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        status = await spark_client.get_cluster_status()
        assert isinstance(status, ClusterStatus)
        assert status.status == "ALIVE"
        assert status.total_cores == 8
        assert status.used_cores == 2
        assert status.total_memory == 16384
        assert status.used_memory == 4096
        assert status.worker_count == 2
        assert status.active_app_count == 1

    @respx.mock
    async def test_cluster_status_http_error(self, spark_client):
        """Test cluster status retrieval with HTTP error."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await spark_client.get_cluster_status()


@pytest.mark.respx_issue
class TestGetWorkers:
    """Tests for get_workers method."""

    @respx.mock
    async def test_successful_workers_retrieval(self, spark_client, mock_spark_master_response):
        """Test successful workers retrieval."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        workers = await spark_client.get_workers()

        assert len(workers) == 2
        assert all(isinstance(w, WorkerInfo) for w in workers)
        assert workers[0].id == "worker-1"
        assert workers[0].host == "localhost"
        assert workers[0].port == 8881
        assert workers[0].cores == 4
        assert workers[0].memory == 8192
        assert workers[0].state == "ALIVE"

    @respx.mock
    async def test_workers_empty_list(self, spark_client):
        """Test workers retrieval with empty list."""
        response_data = {"workers": []}
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=response_data)
        )

        workers = await spark_client.get_workers()

        assert workers == []


@pytest.mark.respx_issue
class TestGetApps:
    """Tests for get_apps method."""

    @respx.mock
    async def test_get_active_apps_only(self, spark_client, mock_spark_master_response):
        """Test retrieving only active apps."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        apps = await spark_client.get_apps(include_completed=False)

        assert len(apps) == 1
        assert all(isinstance(a, AppInfo) for a in apps)
        assert apps[0].id == "app-20241210000001-0001"
        assert apps[0].state == "RUNNING"

    @respx.mock
    async def test_get_apps_with_completed(self, spark_client, mock_spark_master_response):
        """Test retrieving apps including completed ones."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        apps = await spark_client.get_apps(include_completed=True)

        assert len(apps) == 2
        running_apps = [a for a in apps if a.state == "RUNNING"]
        finished_apps = [a for a in apps if a.state == "FINISHED"]
        assert len(running_apps) == 1
        assert len(finished_apps) == 1

@pytest.mark.respx_issue
class TestKillApp:
    """Tests for kill_app method."""
    
    @respx.mock
    async def test_kill_running_app_success(self, spark_client, mock_spark_master_response):
        """Test successfully killing a running app."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{spark_client.master_url}/app/kill/").mock(
            return_value=httpx.Response(200, json={})
        )

        result = await spark_client.kill_app("app-20241210000001-0001")

        assert result.success is True
        assert "killed successfully" in result.message

    @respx.mock
    async def test_kill_nonexistent_app(self, spark_client, mock_spark_master_response):
        """Test killing a non-existent app."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        result = await spark_client.kill_app("app-nonexistent")

        assert result.success is False
        assert "not found" in result.message

    @respx.mock
    async def test_kill_finished_app(self, spark_client, mock_spark_master_response):
        """Test killing a finished app."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )

        result = await spark_client.kill_app("app-20241210000001-0000")

        assert result.success is False
        assert "not in RUNNING state" in result.message

    @respx.mock
    async def test_kill_app_http_error(self, spark_client, mock_spark_master_response):
        """Test killing an app with HTTP error."""
        respx.get(f"{spark_client.master_url}/json/").mock(
            return_value=httpx.Response(200, json=mock_spark_master_response)
        )
        respx.post(f"{spark_client.master_url}/app/kill/").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )

        result = await spark_client.kill_app("app-20241210000001-0001")

        assert result.success is False
        assert "Failed to kill application" in result.message
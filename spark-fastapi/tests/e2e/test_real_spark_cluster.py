"""E2E tests against real Spark cluster.

These tests require a running Spark cluster (via docker-compose).
Set SKIP_E2E=1 environment variable to skip these tests.
"""
import pytest
import os
import httpx
from app.core.config import settings


# Skip E2E tests if SKIP_E2E environment variable is set
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_E2E") == "1",
    reason="E2E tests skipped (SKIP_E2E=1)"
)


@pytest.fixture
async def real_spark_cluster():
    """Check if real Spark cluster is available."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.spark_master_url}/json/", timeout=5.0)
            response.raise_for_status()
            return True
        except (httpx.HTTPError, httpx.ConnectError):
            pytest.skip("Real Spark cluster not available")


class TestRealClusterStatus:
    """E2E tests for cluster status with real Spark cluster."""

    async def test_get_real_cluster_status(self, test_client, real_spark_cluster):
        """Test getting status from real Spark cluster."""
        response = test_client.get("/api/v1/cluster/status")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "total_cores" in data
        assert "used_cores" in data
        assert "total_memory" in data
        assert "used_memory" in data
        assert "worker_count" in data
        assert "active_app_count" in data

        # Validate data types
        assert isinstance(data["total_cores"], int)
        assert isinstance(data["used_cores"], int)
        assert isinstance(data["worker_count"], int)

    async def test_get_real_workers(self, test_client, real_spark_cluster):
        """Test getting workers from real Spark cluster."""
        response = test_client.get("/api/v1/cluster/workers")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # If workers exist, validate structure
        if len(data) > 0:
            worker = data[0]
            assert "id" in worker
            assert "host" in worker
            assert "port" in worker
            assert "cores" in worker
            assert "memory" in worker
            assert "state" in worker

    async def test_get_real_apps(self, test_client, real_spark_cluster):
        """Test getting apps from real Spark cluster."""
        response = test_client.get("/api/v1/jobs/apps")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        # If apps exist, validate structure
        if len(data) > 0:
            app = data[0]
            assert "id" in app
            assert "name" in app
            assert "state" in app
            assert "cores" in app
            assert "memory_per_executor" in app
            assert "submitted_time" in app


class TestRealJobSubmission:
    """E2E tests for job submission with real Spark cluster."""

    async def test_submit_real_job(self, test_client, real_spark_cluster, tmp_path):
        """Test submitting a real Spark job."""
        # Create a simple PySpark script
        script_path = tmp_path / "simple_job.py"
        script_content = """
from pyspark.sql import SparkSession
import time

spark = SparkSession.builder.appName("E2E Test Job").getOrCreate()

# Simple computation
df = spark.range(1000).selectExpr("id", "id * 2 as doubled")
count = df.count()
print(f"Count: {count}")

time.sleep(5)  # Keep job running for a bit
spark.stop()
"""
        script_path.write_text(script_content)

        # Submit the job
        request_data = {
            "script_path": str(script_path),
            "driver_memory": "512m",
            "executor_memory": "512m",
            "executor_cores": 1,
        }
        response = test_client.post("/api/v1/jobs/submit", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "PID" in data["message"]

    async def test_kill_real_job(self, test_client, real_spark_cluster, tmp_path):
        """Test killing a real running job."""
        # First, submit a long-running job
        script_path = tmp_path / "long_running_job.py"
        script_content = """
from pyspark.sql import SparkSession
import time

spark = SparkSession.builder.appName("Long Running Test Job").getOrCreate()

# Keep the job running
for i in range(100):
    df = spark.range(100).selectExpr("id")
    df.count()
    time.sleep(1)

spark.stop()
"""
        script_path.write_text(script_content)

        # Submit the job
        request_data = {
            "script_path": str(script_path),
            "driver_memory": "512m",
            "executor_memory": "512m",
            "executor_cores": 1,
        }
        submit_response = test_client.post("/api/v1/jobs/submit", json=request_data)
        assert submit_response.status_code == 200

        # Wait a bit for the job to appear in the cluster
        import asyncio
        await asyncio.sleep(5)

        # Get the running apps
        apps_response = test_client.get("/api/v1/jobs/apps")
        apps = apps_response.json()

        # Find our test job
        test_jobs = [app for app in apps if "Long Running Test Job" in app["name"]]

        if test_jobs:
            app_id = test_jobs[0]["id"]

            # Kill the job
            kill_response = test_client.delete(f"/api/v1/jobs/apps/{app_id}")

            assert kill_response.status_code == 200
            data = kill_response.json()
            assert data["success"] is True
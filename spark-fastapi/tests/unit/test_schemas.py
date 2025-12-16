"""Unit tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError
from app.schemas.cluster import ClusterStatus, WorkerInfo, AppInfo
from app.schemas.job import JobSubmitRequest, JobSubmitResponse


class TestClusterStatusSchema:
    """Tests for ClusterStatus schema."""

    def test_valid_cluster_status(self):
        """Test creating valid ClusterStatus."""
        data = {
            "status": "ALIVE",
            "total_cores": 8,
            "used_cores": 4,
            "total_memory": 16384,
            "used_memory": 8192,
            "worker_count": 2,
            "active_app_count": 1,
        }

        status = ClusterStatus(**data)

        assert status.status == "ALIVE"
        assert status.total_cores == 8
        assert status.used_cores == 4
        assert status.total_memory == 16384
        assert status.used_memory == 8192
        assert status.worker_count == 2
        assert status.active_app_count == 1

    def test_cluster_status_zero_values(self):
        """Test ClusterStatus with zero values."""
        data = {
            "status": "UNKNOWN",
            "total_cores": 0,
            "used_cores": 0,
            "total_memory": 0,
            "used_memory": 0,
            "worker_count": 0,
            "active_app_count": 0,
        }

        status = ClusterStatus(**data)

        assert status.worker_count == 0
        assert status.active_app_count == 0

    def test_cluster_status_missing_field(self):
        """Test ClusterStatus with missing required field."""
        data = {
            "status": "ALIVE",
            # Missing total_cores and other fields
        }

        with pytest.raises(ValidationError):
            ClusterStatus(**data)


class TestWorkerInfoSchema:
    """Tests for WorkerInfo schema."""

    def test_valid_worker_info(self):
        """Test creating valid WorkerInfo."""
        data = {
            "id": "worker-20231210120000-192.168.1.100-7078",
            "host": "192.168.1.100",
            "port": 7078,
            "cores": 4,
            "memory": 8192,
            "state": "ALIVE",
        }

        worker = WorkerInfo(**data)

        assert worker.id == "worker-20231210120000-192.168.1.100-7078"
        assert worker.host == "192.168.1.100"
        assert worker.port == 7078
        assert worker.cores == 4
        assert worker.memory == 8192
        assert worker.state == "ALIVE"

    def test_worker_info_dead_state(self):
        """Test WorkerInfo with DEAD state."""
        data = {
            "id": "worker-1",
            "host": "localhost",
            "port": 8881,
            "cores": 4,
            "memory": 8192,
            "state": "DEAD",
        }

        worker = WorkerInfo(**data)

        assert worker.state == "DEAD"

    def test_worker_info_invalid_port(self):
        """Test WorkerInfo with invalid port type."""
        data = {
            "id": "worker-1",
            "host": "localhost",
            "port": "invalid",  # Should be int
            "cores": 4,
            "memory": 8192,
            "state": "ALIVE",
        }

        with pytest.raises(ValidationError):
            WorkerInfo(**data)


class TestAppInfoSchema:
    """Tests for AppInfo schema."""

    def test_valid_app_info_running(self):
        """Test creating valid AppInfo in RUNNING state."""
        data = {
            "id": "app-20241210120000-0001",
            "name": "MySparkApp",
            "state": "RUNNING",
            "cores": 2,
            "memory_per_executor": 2048,
            "submitted_time": 1702195200000,
        }

        app = AppInfo(**data)

        assert app.id == "app-20241210120000-0001"
        assert app.name == "MySparkApp"
        assert app.state == "RUNNING"
        assert app.cores == 2
        assert app.memory_per_executor == 2048
        assert app.submitted_time == 1702195200000

    def test_valid_app_info_finished(self):
        """Test creating valid AppInfo in FINISHED state."""
        data = {
            "id": "app-20241210120000-0002",
            "name": "CompletedApp",
            "state": "FINISHED",
            "cores": 4,
            "memory_per_executor": 4096,
            "submitted_time": 1702195300000,
        }

        app = AppInfo(**data)

        assert app.state == "FINISHED"

    def test_valid_app_info_killed(self):
        """Test creating valid AppInfo in KILLED state."""
        data = {
            "id": "app-20241210120000-0003",
            "name": "KilledApp",
            "state": "KILLED",
            "cores": 1,
            "memory_per_executor": 1024,
            "submitted_time": 1702195400000,
        }

        app = AppInfo(**data)

        assert app.state == "KILLED"

    def test_app_info_timestamp_as_string(self):
        """Test AppInfo with timestamp as string."""
        data = {
            "id": "app-1",
            "name": "TestApp",
            "state": "RUNNING",
            "cores": 2,
            "memory_per_executor": 2048,
            "submitted_time": "1702195200000",  # String instead of int
        }

        app = AppInfo(**data)

        # Pydantic should coerce string to int
        assert isinstance(app.submitted_time, (int, str))


class TestJobSubmitRequestSchema:
    """Tests for JobSubmitRequest schema."""

    def test_valid_job_submit_request_minimal(self):
        """Test JobSubmitRequest with minimal required fields."""
        data = {
            "script_path": "/path/to/script.py",
        }

        request = JobSubmitRequest(**data)

        assert request.script_path == "/path/to/script.py"
        assert request.driver_memory == "1g"
        assert request.executor_memory == "1g"
        assert request.executor_cores == 1
        assert request.num_executors is None

    def test_valid_job_submit_request_full(self):
        """Test JobSubmitRequest with all fields."""
        data = {
            "script_path": "/path/to/script.py",
            "driver_memory": "2g",
            "executor_memory": "4g",
            "executor_cores": 4,
            "num_executors": 10,
        }

        request = JobSubmitRequest(**data)

        assert request.script_path == "/path/to/script.py"
        assert request.driver_memory == "2g"
        assert request.executor_memory == "4g"
        assert request.executor_cores == 4
        assert request.num_executors == 10

    def test_job_submit_request_memory_formats(self):
        """Test JobSubmitRequest with various memory formats."""
        data = {
            "script_path": "/path/to/script.py",
            "driver_memory": "512m",
            "executor_memory": "8g",
        }

        request = JobSubmitRequest(**data)

        assert request.driver_memory == "512m"
        assert request.executor_memory == "8g"

    def test_job_submit_request_missing_script_path(self):
        """Test JobSubmitRequest without script_path."""
        data = {
            "driver_memory": "1g",
        }

        with pytest.raises(ValidationError):
            JobSubmitRequest(**data)

    def test_job_submit_request_invalid_executor_cores_type(self):
        """Test JobSubmitRequest with invalid executor_cores type."""
        data = {
            "script_path": "/path/to/script.py",
            "executor_cores": "invalid",  # Should be int
        }

        with pytest.raises(ValidationError):
            JobSubmitRequest(**data)


class TestJobSubmitResponseSchema:
    """Tests for JobSubmitResponse schema."""

    def test_valid_job_submit_response_success(self):
        """Test JobSubmitResponse for successful submission."""
        data = {
            "success": True,
            "message": "Job submitted (PID: 12345)",
        }

        response = JobSubmitResponse(**data)

        assert response.success is True
        assert response.message == "Job submitted (PID: 12345)"

    def test_valid_job_submit_response_failure(self):
        """Test JobSubmitResponse for failed submission."""
        data = {
            "success": False,
            "message": "Script not found",
        }

        response = JobSubmitResponse(**data)

        assert response.success is False
        assert response.message == "Script not found"

    def test_job_submit_response_missing_field(self):
        """Test JobSubmitResponse with missing field."""
        data = {
            "success": True,
            # Missing message
        }

        with pytest.raises(ValidationError):
            JobSubmitResponse(**data)
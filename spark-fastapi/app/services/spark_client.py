import asyncio

import httpx
from app.core.config import settings
from app.schemas.cluster import AppInfo, ClusterStatus, WorkerInfo
from app.schemas.job import JobSubmitRequest, JobSubmitResponse


class SparkClient:
    def __init__(self):
        self.master_url = settings.spark_master_url
        self.spark_submit_master = settings.spark_submit_master
        self.spark_home = settings.spark_home

    async def get_cluster_status(self) -> ClusterStatus:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.master_url}/json/")
            response.raise_for_status()
            data = response.json()

            return ClusterStatus(
                status=data.get("status", "UNKNOWN"),
                total_cores=data.get("cores", 0),
                used_cores=data.get("coresused", 0),
                total_memory=data.get("memory", 0),
                used_memory=data.get("memoryused", 0),
                worker_count=len(data.get("workers", [])),
                active_app_count=len(data.get("activeapps", [])),
            )

    async def get_workers(self) -> list[WorkerInfo]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.master_url}/json/")
            response.raise_for_status()
            data = response.json()

            return [
                WorkerInfo(
                    id=w["id"],
                    host=w["host"],
                    port=w["port"],
                    cores=w["cores"],
                    memory=w["memory"],
                    state=w["state"],
                )
                for w in data.get("workers", [])
            ]

    async def get_apps(self, include_completed: bool = False) -> list[AppInfo]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.master_url}/json/")
            response.raise_for_status()
            data = response.json()

            apps = []
            for app in data.get("activeapps", []):
                apps.append(
                    AppInfo(
                        id=app["id"],
                        name=app["name"],
                        state=app.get("state", "RUNNING"),
                        cores=app.get("cores", 0),
                        memory_per_executor=app.get("memoryperslave", 0),
                        submitted_time=app.get("starttime", ""),
                    )
                )

            if include_completed:
                for app in data.get("completedapps", []):
                    apps.append(
                        AppInfo(
                            id=app["id"],
                            name=app["name"],
                            state=app.get("state", "FINISHED"),
                            cores=app.get("cores", 0),
                            memory_per_executor=app.get("memoryperslave", 0),
                            submitted_time=app.get("starttime", ""),
                        )
                    )

            return apps

    async def get_app(self, app_id: str) -> AppInfo | None:
        apps = await self.get_apps(include_completed=True)
        for app in apps:
            if app.id == app_id:
                return app
        return None

    async def kill_app(self, app_id: str) -> JobSubmitResponse:
        """Kill a running Spark application"""
        # Check if app exists and get its state
        app = await self.get_app(app_id)

        if not app:
            return JobSubmitResponse(
                success=False,
                message=f"Application {app_id} not found",
            )

        if app.state != "RUNNING":
            return JobSubmitResponse(
                success=False,
                message=f"Application {app_id} is not in RUNNING state (current: {app.state})",
            )

        # Kill the application using POST request to Spark Master
        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                response = await client.post(
                    f"{self.master_url}/app/kill/",
                    data={"id": app_id, "terminate": "true"}
                )

                # Spark Master returns 302 redirect on successful kill
                if response.status_code in [200, 302]:
                    return JobSubmitResponse(
                        success=True,
                        message=f"Application {app_id} killed successfully",
                    )

                return JobSubmitResponse(
                    success=False,
                    message=f"Failed to kill application: HTTP {response.status_code}",
                )
            except httpx.HTTPError as e:
                return JobSubmitResponse(
                    success=False,
                    message=f"Failed to kill application: {str(e)}",
                )

    async def submit_job(self, request: JobSubmitRequest, script_path: str) -> JobSubmitResponse:
        spark_submit = f"{self.spark_home}/bin/spark-submit"

        cmd = [
            spark_submit,
            "--master", self.spark_submit_master,
            "--deploy-mode", "client",
            "--driver-memory", request.driver_memory,
            "--executor-memory", request.executor_memory,
            "--executor-cores", str(request.executor_cores),
            "--packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.hadoop:hadoop-aws:3.3.4,software.amazon.awssdk:bundle:2.21.42,org.postgresql:postgresql:42.7.3"
        ]

        if request.num_executors:
            cmd.extend(["--num-executors", str(request.num_executors)])

        cmd.append(script_path)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            return JobSubmitResponse(
                success=True,
                message=f"Job submitted (PID: {process.pid})",
            )
        except Exception as e:
            return JobSubmitResponse(
                success=False,
                message=str(e),
            )


spark_client = SparkClient()
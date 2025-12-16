from fastapi import APIRouter, HTTPException
from pathlib import Path
import httpx

from app.schemas.job import JobSubmitRequest, JobSubmitResponse
from app.schemas.cluster import AppInfo
from app.services.spark_client import spark_client

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/submit", response_model=JobSubmitResponse)
async def submit_job(request: JobSubmitRequest):
    full_path = Path(request.script_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Script not found: {request.script_path}")
    if not full_path.suffix == ".py":
        raise HTTPException(status_code=400, detail="Only .py files are allowed")

    result = await spark_client.submit_job(request, str(full_path))
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.get("/apps", response_model=list[AppInfo])
async def get_apps(include_completed: bool = False):
    """Get list of Spark applications"""
    try:
        return await spark_client.get_apps(include_completed=include_completed)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Spark cluster connection failed: {e}")


@router.get("/apps/{app_id}", response_model=AppInfo)
async def get_app(app_id: str):
    """Get a specific Spark application by ID"""
    try:
        app = await spark_client.get_app(app_id)
        if app is None:
            raise HTTPException(status_code=404, detail=f"App {app_id} not found")
        return app
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Spark cluster connection failed: {e}")


@router.delete("/apps/{app_id}", response_model=JobSubmitResponse)
async def kill_job(app_id: str):
    """Kill a running Spark application by app_id"""
    result = await spark_client.kill_app(app_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result
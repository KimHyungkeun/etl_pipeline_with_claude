from fastapi import APIRouter, HTTPException
import httpx

from app.schemas.cluster import ClusterStatus, WorkerInfo
from app.services.spark_client import spark_client

router = APIRouter(prefix="/cluster", tags=["cluster"])


@router.get("/status", response_model=ClusterStatus)
async def get_cluster_status():
    try:
        return await spark_client.get_cluster_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Spark cluster connection failed: {e}")


@router.get("/workers", response_model=list[WorkerInfo])
async def get_workers():
    try:
        return await spark_client.get_workers()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Spark cluster connection failed: {e}")
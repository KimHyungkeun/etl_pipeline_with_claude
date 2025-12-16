from fastapi import APIRouter

from app.api.endpoints import cluster, jobs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(cluster.router)
api_router.include_router(jobs.router)
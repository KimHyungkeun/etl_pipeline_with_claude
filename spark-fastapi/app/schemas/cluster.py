from pydantic import BaseModel


class ClusterStatus(BaseModel):
    status: str
    total_cores: int
    used_cores: int
    total_memory: int
    used_memory: int
    worker_count: int
    active_app_count: int


class WorkerInfo(BaseModel):
    id: str
    host: str
    port: int
    cores: int
    memory: int
    state: str


class AppInfo(BaseModel):
    id: str
    name: str
    state: str
    cores: int
    memory_per_executor: int
    submitted_time: int  # timestamp (milliseconds)
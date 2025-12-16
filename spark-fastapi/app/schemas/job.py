from pydantic import BaseModel


class JobSubmitRequest(BaseModel):
    script_path: str  # 스크립트 파일 경로 (예: "/path/to/my_job.py")
    driver_memory: str = "1g"
    executor_memory: str = "1g"
    executor_cores: int = 1
    num_executors: int | None = None


class JobSubmitResponse(BaseModel):
    success: bool
    message: str
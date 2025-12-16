export interface ClusterStatus {
  status: string;
  total_cores: number;
  used_cores: number;
  total_memory: number;
  used_memory: number;
  worker_count: number;
  active_app_count: number;
}

export interface WorkerInfo {
  id: string;
  host: string;
  port: number;
  cores: number;
  memory: number;
  state: string;
}

export interface AppInfo {
  id: string;
  name: string;
  state: string;
  cores: number;
  memory_per_executor: number;
  submitted_time: string;
}

export interface JobSubmitRequest {
  script_path: string;
  driver_memory?: string;
  executor_memory?: string;
  executor_cores?: number;
  num_executors?: number;
}

export interface JobSubmitResponse {
  success: boolean;
  message: string;
  job_id?: string;
}

import type { ClusterStatus } from '@/shared/types/types';
import { formatMemory } from '@/shared/lib/format';

interface Props {
  status: ClusterStatus | null;
  error: string | null;
}

export function ClusterStatusCard({ status, error }: Props) {
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-red-800">Cluster Status</h2>
        <p className="text-red-600 mt-2">{error}</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800">Cluster Status</h2>
        <p className="text-gray-500 mt-2">Loading...</p>
      </div>
    );
  }

  const statusColor = status.status === 'ALIVE' ? 'green' : 'red';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Cluster Status</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="text-center">
          <p className="text-sm text-gray-500">Status</p>
          <p className={`text-lg font-bold text-${statusColor}-600`}>
            {status.status}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Cores</p>
          <p className="text-lg font-bold text-gray-800">
            {status.used_cores} / {status.total_cores}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Memory</p>
          <p className="text-lg font-bold text-gray-800">
            {formatMemory(status.used_memory)} / {formatMemory(status.total_memory)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Workers</p>
          <p className="text-lg font-bold text-gray-800">{status.worker_count}</p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Active Apps</p>
          <p className="text-lg font-bold text-gray-800">{status.active_app_count}</p>
        </div>
      </div>
    </div>
  );
}
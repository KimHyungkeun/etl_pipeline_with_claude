import { useState, useCallback } from 'react';
import { ClusterStatusCard } from '@/features/cluster/ui/ClusterStatusCard';
import { WorkerList } from '@/features/cluster/ui/WorkerList';
import { AppList } from '@/features/cluster/ui/AppList';
import { JobSubmitForm } from '@/features/job-submit/ui/JobSubmitForm';
import { usePolling } from '@/shared/lib/usePolling';
import { getClusterStatus, getWorkers, getApps } from '@/shared/api/spark';
import type { ClusterStatus, WorkerInfo, AppInfo } from '@/shared/types/types';

export function App() {
  const [status, setStatus] = useState<ClusterStatus | null>(null);
  const [workers, setWorkers] = useState<WorkerInfo[]>([]);
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statusData, workersData, appsData] = await Promise.all([
        getClusterStatus(),
        getWorkers(),
        getApps(includeCompleted),
      ]);
      setStatus(statusData);
      setWorkers(workersData);
      setApps(appsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    }
  }, [includeCompleted]);

  usePolling(fetchData, { interval: 5000, enabled: autoRefresh });

  const handleRefresh = async () => {
    await fetchData();
    setShowToast(true);
    setTimeout(() => setShowToast(false), 2000);
  };

  const handleJobSuccess = () => {
    setTimeout(fetchData, 1000);
  };

  const handleJobKilled = () => {
    setTimeout(fetchData, 1000);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {showToast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-4 py-2 rounded-md shadow-lg text-sm font-medium">
          Refresh Complete
        </div>
      )}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">Spark Cluster Manager</h1>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300"
              />
              Auto-refresh (5s)
            </label>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <ClusterStatusCard status={status} error={error} />
        <WorkerList workers={workers} />
        <AppList
          apps={apps}
          includeCompleted={includeCompleted}
          onToggleCompleted={setIncludeCompleted}
          onJobKilled={handleJobKilled}
        />
        <JobSubmitForm onSuccess={handleJobSuccess} />
      </main>
    </div>
  );
}
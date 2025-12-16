import { useState } from 'react';
import type { AppInfo } from '@/shared/types/types';
import { formatMemory, formatTime } from '@/shared/lib/format';
import { killJob } from '@/shared/api/spark';

interface Props {
  apps: AppInfo[];
  includeCompleted: boolean;
  onToggleCompleted: (value: boolean) => void;
  onJobKilled: () => void;
}

export function AppList({ apps, includeCompleted, onToggleCompleted, onJobKilled }: Props) {
  const [selectedApps, setSelectedApps] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const runningApps = apps.filter(app => app.state === 'RUNNING');

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedApps(new Set(runningApps.map(app => app.id)));
    } else {
      setSelectedApps(new Set());
    }
  };

  const handleSelectApp = (appId: string, checked: boolean) => {
    const newSelected = new Set(selectedApps);
    if (checked) {
      newSelected.add(appId);
    } else {
      newSelected.delete(appId);
    }
    setSelectedApps(newSelected);
  };

  const handleStopJobs = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const promises = Array.from(selectedApps).map(appId => killJob(appId));
      await Promise.all(promises);

      setMessage({
        type: 'success',
        text: `Successfully stopped ${selectedApps.size} job(s)`
      });
      setSelectedApps(new Set());
      onJobKilled();

      // Auto-hide success message after 3 seconds
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to stop jobs'
      });
    } finally {
      setLoading(false);
    }
  };

  const allSelected = runningApps.length > 0 && selectedApps.size === runningApps.length;
  const someSelected = selectedApps.size > 0 && selectedApps.size < runningApps.length;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Running Applications</h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={includeCompleted}
              onChange={(e) => onToggleCompleted(e.target.checked)}
              className="rounded border-gray-300"
            />
            All State
          </label>
          <button
            onClick={handleStopJobs}
            disabled={selectedApps.size === 0 || loading}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium"
          >
            {loading ? 'Stopping...' : 'Stop'}
          </button>
        </div>
      </div>

      {message && (
        <div
          className={`mb-4 p-3 rounded-md ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          {message.text}
        </div>
      )}

      {apps.length === 0 ? (
        <p className="text-gray-500">No applications</p>
      ) : (
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <div className="overflow-x-auto">
            <div className="max-h-[330px] overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-1.5 text-left bg-gray-50 w-12">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        ref={input => {
                          if (input) input.indeterminate = someSelected;
                        }}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                        disabled={runningApps.length === 0}
                        className="rounded border-gray-300"
                      />
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-64">
                      ID
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50">
                      Name
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-28">
                      State
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-20">
                      Cores
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-36">
                      Mem Per Executor
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-44">
                      Submitted
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {apps.map((app) => (
                    <tr key={app.id}>
                      <td className="px-3 py-1.5 w-12">
                        <input
                          type="checkbox"
                          checked={selectedApps.has(app.id)}
                          onChange={(e) => handleSelectApp(app.id, e.target.checked)}
                          disabled={app.state !== 'RUNNING'}
                          className="rounded border-gray-300"
                        />
                      </td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 font-mono w-64">
                        {app.id}
                      </td>
                      <td className="px-3 py-1.5 text-sm text-gray-900">{app.name}</td>
                      <td className="px-3 py-1.5 text-sm w-28">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            app.state === 'RUNNING'
                              ? 'bg-blue-100 text-blue-800'
                              : app.state === 'FINISHED'
                              ? 'bg-green-100 text-green-800'
                              : app.state === 'KILLED'
                              ? 'bg-red-100 text-red-800'
                              : app.state === 'FAILED'
                              ? 'bg-orange-100 text-orange-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {app.state}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 w-20">{app.cores}</td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 w-36">
                        {formatMemory(app.memory_per_executor)}
                      </td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 w-44">
                        {formatTime(app.submitted_time)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
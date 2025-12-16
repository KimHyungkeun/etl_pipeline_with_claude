import { useState } from 'react';
import type { JobSubmitRequest } from '@/shared/types/types';
import { submitJob } from '@/shared/api/spark';

interface Props {
  onSuccess: () => void;
}

export function JobSubmitForm({ onSuccess }: Props) {
  const [form, setForm] = useState<JobSubmitRequest>({
    script_path: '/home/hkkim/etl-cluster-test/iot-pipeline/spark-jobs/pyspark-jobs/batch_aggregation.py',
    driver_memory: '1g',
    executor_memory: '1g',
    executor_cores: 1,
    num_executors: undefined,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    // .py 확장자 체크
    if (!form.script_path.endsWith('.py')) {
      setMessage({ type: 'error', text: 'Only pyspark(.py) Allowed' });

      // Auto-hide success message after 3 seconds
      setTimeout(() => setMessage(null), 3000);
      return;
    }

    setLoading(true);

    try {
      const response = await submitJob(form);
      if (response.success) {
        setMessage({ type: 'success', text: response.message });
        onSuccess();

        // Auto-hide success message after 3 seconds
        setTimeout(() => setMessage(null), 3000);
      } else {
        setMessage({ type: 'error', text: response.message });

        // Auto-hide success message after 3 seconds
        setTimeout(() => setMessage(null), 3000);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      // 파일 미존재 에러 처리
      if (errorMsg.includes('Script not found') || errorMsg.includes('not found')) {
        setMessage({ type: 'error', text: `No such Path: ${form.script_path}` });
        
        // Auto-hide success message after 3 seconds
        setTimeout(() => setMessage(null), 3000);
      } else {
        setMessage({ type: 'error', text: errorMsg });
        
        // Auto-hide success message after 3 seconds
        setTimeout(() => setMessage(null), 3000);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Submit Job</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Script Path (.py)
          </label>
          <input
            type="text"
            value={form.script_path}
            onChange={(e) => setForm({ ...form, script_path: e.target.value })}
            placeholder="/path/to/your/script.py"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Driver Memory
            </label>
            <input
              type="text"
              value={form.driver_memory}
              onChange={(e) => setForm({ ...form, driver_memory: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Executor Memory
            </label>
            <input
              type="text"
              value={form.executor_memory}
              onChange={(e) => setForm({ ...form, executor_memory: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Executor Cores
            </label>
            <input
              type="number"
              value={form.executor_cores}
              onChange={(e) => setForm({ ...form, executor_cores: parseInt(e.target.value) || 1 })}
              min={1}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Num Executors
            </label>
            <input
              type="number"
              value={form.num_executors || ''}
              onChange={(e) => setForm({ ...form, num_executors: e.target.value ? parseInt(e.target.value) : undefined })}
              placeholder="auto"
              min={1}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {message && (
          <div
            className={`p-3 rounded-md ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full md:w-auto px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {loading ? 'Submitting...' : 'Submit Job'}
          </button>
        </div>
      </form>
    </div>
  );
}
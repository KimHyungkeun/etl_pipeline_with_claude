import type { WorkerInfo } from '@/shared/types/types';
import { formatMemory } from '@/shared/lib/format';

interface Props {
  workers: WorkerInfo[];
}

export function WorkerList({ workers }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Workers</h2>
      {workers.length === 0 ? (
        <p className="text-gray-500">No workers available</p>
      ) : (
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <div className="overflow-x-auto">
            <div className="max-h-[330px] overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-80">
                      ID
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50">
                      Host
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-24">
                      Port
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-20">
                      Cores
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-32">
                      Memory
                    </th>
                    <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50 w-24">
                      State
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {workers.map((worker) => (
                    <tr key={worker.id}>
                      <td className="px-3 py-1.5 text-sm text-gray-900 font-mono w-80">
                        {worker.id}
                      </td>
                      <td className="px-3 py-1.5 text-sm text-gray-900">{worker.host}</td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 w-24">{worker.port}</td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 w-20">{worker.cores}</td>
                      <td className="px-3 py-1.5 text-sm text-gray-900 w-32">
                        {formatMemory(worker.memory)}
                      </td>
                      <td className="px-3 py-1.5 text-sm w-24">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            worker.state === 'ALIVE'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {worker.state}
                        </span>
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
export function formatMemory(mb: number): string {
  // Input is in MB (from Spark Master API), always display in MB
  return `${mb} MB`;
}

export function formatTime(timestamp: string | number): string {
  if (!timestamp) return '-';
  return new Date(timestamp).toLocaleString();
}
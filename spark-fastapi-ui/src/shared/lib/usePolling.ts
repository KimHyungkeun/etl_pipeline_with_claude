import { useEffect, useRef, useCallback } from 'react';

interface UsePollingOptions {
  interval: number;
  enabled: boolean;
}

export function usePolling(
  callback: () => Promise<void>,
  options: UsePollingOptions
) {
  const { interval, enabled } = options;
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  const tick = useCallback(async () => {
    await savedCallback.current();
  }, []);

  useEffect(() => {
    if (!enabled) return;

    tick();

    const id = setInterval(tick, interval);
    return () => clearInterval(id);
  }, [enabled, interval, tick]);
}
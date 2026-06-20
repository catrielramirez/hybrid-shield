import { useState, useEffect } from 'react';
import { MOCK_JOBS } from './mockData';
import type { Job } from '../hooks/useLiveJobs';

/**
 * Mock implementation of useLiveJobs that returns static data.
 * Activated when NEXT_PUBLIC_DATA_SOURCE=mock
 */
export function useMockLiveJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Simulate initial loading delay (800ms)
    const timer = setTimeout(() => {
      // Convert MockJob[] to Job[] (compatible interfaces)
      setJobs(MOCK_JOBS as unknown as Job[]);
      setLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  return { jobs, loading, error };
}

import { useState, useEffect } from 'react';
import { collection, query, orderBy, onSnapshot, limit } from 'firebase/firestore';
import { db, isMockMode } from '../firebase';
import { useMockLiveJobs } from '../mock/useMockLiveJobs';

export interface Job {
  id: string;
  status: string; // PENDING, EXTRACTOR, RAG, DECISION, Needs Review, Done, ERROR
  flow?: number; // 1, 2, 3, 4
  title?: string;
  description?: string;
  price?: number;
  result?: string;
  reasons?: string[];
  last_update?: string;
  gcs_image_uri?: string;
  extracted_features?: any;
  risk_assessment?: any;
  rag_results?: any;
  final_decision?: any;
}

export function useLiveJobs() {
  // Redirect to mock in mock mode
  if (isMockMode) return useMockLiveJobs();
  
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Escuchar los ultimos 20 jobs ordenados por ultima actualizacion
    const q = query(
      collection(db, 'jobs'),
      orderBy('last_update', 'desc'),
      limit(20)
    );

    const unsubscribe = onSnapshot(q, 
      (snapshot) => {
        const jobsData: Job[] = [];
        snapshot.forEach((doc) => {
          jobsData.push({ id: doc.id, ...doc.data() } as Job);
        });
        setJobs(jobsData);
        setLoading(false);
      },
      (err) => {
        console.error("Error listening to jobs:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { jobs, loading, error };
}

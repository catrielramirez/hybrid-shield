import { motion, AnimatePresence } from 'framer-motion';
import { LiveVerdictCard } from './LiveVerdictCard';
import type { Job } from '../../lib/hooks/useLiveJobs';

interface LiveStreamFeedProps {
  jobs: Job[];
  loading: boolean;
  onReviewClick: (job: Job) => void;
}

export function LiveStreamFeed({ jobs, loading, onReviewClick }: LiveStreamFeedProps) {
  if (loading) {
    return (
      <div className="flex flex-col gap-4 w-full">
        {[1, 2, 3].map(i => (
          <div key={i} className="glass-panel h-24 rounded-2xl animate-pulse bg-white/40" />
        ))}
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 glass-panel rounded-3xl text-slate-400">
        <div className="w-3 h-3 rounded-full bg-slate-300 animate-pulse mb-4" />
        <p className="text-sm font-medium">Esperando flujo de moderación...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full relative">
      <AnimatePresence mode="popLayout">
        {jobs.map((job) => (
          <LiveVerdictCard 
            key={job.id} 
            job={job} 
            onReviewClick={onReviewClick} 
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

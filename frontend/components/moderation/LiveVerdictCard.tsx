import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, CheckCircle2, ShieldAlert, AlertTriangle, Eye } from 'lucide-react';
import type { Job } from '../../lib/hooks/useLiveJobs';
import { LangGraphVisualizer } from './LangGraphVisualizer';

export function LiveVerdictCard({ job, onReviewClick }: { job: Job, onReviewClick: (job: Job) => void }) {
  const [expanded, setExpanded] = useState(false);

  const isApproved = job.status === 'Done' && job.flow === 2;
  const isHitl = job.status === 'Needs Review';
  const isBlocked = job.status === 'Done' && (job.flow === 1 || job.flow === 3);
  const isProcessing = !isApproved && !isHitl && !isBlocked && job.status !== 'ERROR';

  // Determine colors using Tailwind for glassmorphism
  let bgColorClass = 'bg-white/60';
  let borderColorClass = 'border-slate-200/50';
  let Icon = Eye;
  let iconColor = 'text-slate-400';

  if (isApproved) {
    bgColorClass = 'bg-emerald-50/80';
    borderColorClass = 'border-emerald-200';
    Icon = CheckCircle2;
    iconColor = 'text-emerald-600';
  } else if (isHitl) {
    bgColorClass = 'bg-amber-50/80';
    borderColorClass = 'border-amber-200';
    Icon = AlertTriangle;
    iconColor = 'text-amber-600';
  } else if (isBlocked) {
    bgColorClass = 'bg-rose-50/80';
    borderColorClass = 'border-rose-200';
    Icon = ShieldAlert;
    iconColor = 'text-rose-600';
  } else if (isProcessing) {
    bgColorClass = 'bg-white/60';
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`relative backdrop-blur-xl border rounded-2xl overflow-hidden mb-4 transition-colors duration-500 ${bgColorClass} ${borderColorClass} ${isProcessing ? 'shadow-sm shadow-indigo-500/5' : 'shadow-md'}`}
    >
      {isProcessing && (
        <motion.div 
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -skew-x-12"
          initial={{ x: '-100%' }}
          animate={{ x: '200%' }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
      )}
      <div 
        className="p-5 flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          {job.gcs_image_uri ? (
            // In a real app we'd convert GCS URI to a signed URL or public URL
            // For now, placeholder for the image thumbnail
            <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center overflow-hidden shrink-0">
               <img 
                src={job.gcs_image_uri.replace("gs://", "https://storage.googleapis.com/")} 
                alt="Product" 
                className="w-full h-full object-cover"
                onError={(e) => { e.currentTarget.src = "https://placehold.co/100x100/e2e8f0/64748b?text=IMG" }}
               />
            </div>
          ) : (
            <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0">
              <Icon className={`w-5 h-5 ${iconColor}`} />
            </div>
          )}
          <div>
            <h4 className="font-semibold text-slate-800 tracking-tight">
              {job.title || `Job ${job.id.slice(0,6)}`}
            </h4>
            <p className="text-xs text-slate-500 flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full bg-white/60 font-medium ${iconColor}`}>
                {job.status}
              </span>
              {job.price && <span>${job.price}</span>}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {isHitl && (
            <motion.button 
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-4 py-1.5 bg-amber-500/10 text-amber-700 text-xs font-semibold rounded-full border border-amber-500/20"
              onClick={(e) => { e.stopPropagation(); onReviewClick(job); }}
            >
              Revisar
            </motion.button>
          )}
          <motion.div animate={{ rotate: expanded ? 180 : 0 }}>
            <ChevronDown className="w-5 h-5 text-slate-400" />
          </motion.div>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-5 pb-5 pt-2 border-t border-black/5"
          >
            <div className="py-2">
              <LangGraphVisualizer status={job.status} />
            </div>
            
            {(job.result || (job.reasons && job.reasons.length > 0)) && (
              <div className="mt-4 p-4 rounded-xl bg-white/40 text-sm">
                <div className="font-medium mb-1 text-slate-700">Resolución:</div>
                <div className="text-slate-600">{job.result}</div>
                {job.reasons && job.reasons.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {job.reasons.map((r, i) => (
                      <li key={i} className="text-slate-500 flex gap-2 before:content-['•'] before:text-slate-300">
                        {r}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Check, XCircle } from 'lucide-react';
import type { Job } from '../../lib/hooks/useLiveJobs';

interface HitlReviewPanelProps {
  job: Job | null;
  onClose: () => void;
  onDecision: (jobId: string, approved: boolean) => void;
}

export function HitlReviewPanel({ job, onClose, onDecision }: HitlReviewPanelProps) {
  
  useEffect(() => {
    if (!job) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'a') {
        onDecision(job.id, true);
      } else if (e.key.toLowerCase() === 'r') {
        onDecision(job.id, false);
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [job, onDecision, onClose]);

  return (
    <AnimatePresence>
      {job && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: -20, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-4xl max-h-[90vh] overflow-y-auto glass-panel rounded-3xl shadow-2xl bg-white/90"
          >
            <div className="sticky top-0 z-10 flex items-center justify-between p-6 border-b border-slate-100 bg-white/80 backdrop-blur-md">
              <div>
                <h2 className="text-xl font-bold text-slate-800 tracking-tight">Revisión Humana (HITL)</h2>
                <p className="text-sm text-slate-500">ID: {job.id}</p>
              </div>
              <button 
                onClick={onClose}
                className="p-2 rounded-full hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left Column: Media & Product Details */}
              <div className="space-y-6">
                {/* Image placeholder for real app we'd load signed URI */}
                <div className="aspect-square rounded-2xl bg-slate-100 overflow-hidden border border-slate-200">
                  <img 
                    src={"https://placehold.co/400x400/e2e8f0/64748b?text=Product+Image"} 
                    alt="Analizado" 
                    className="w-full h-full object-cover mix-blend-multiply" 
                  />
                </div>
                
                <div className="space-y-2">
                  <h3 className="font-semibold text-slate-800 text-lg">{job.title || 'Sin Título'}</h3>
                  <p className="text-slate-600 text-sm">{job.description || 'Sin Descripción'}</p>
                  <p className="text-slate-800 font-medium">Precio: ${job.price}</p>
                </div>
              </div>

              {/* Right Column: AI Analysis */}
              <div className="space-y-6">
                
                {job.reasons && job.reasons.length > 0 && (
                  <div className="p-4 rounded-2xl bg-amber-50 border border-amber-100">
                    <h4 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" /> Alertas Detectadas
                    </h4>
                    <ul className="space-y-2">
                      {job.reasons.map((r, i) => (
                        <li key={i} className="text-sm text-amber-700 flex gap-2">
                          <span className="mt-0.5">•</span> {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="p-4 rounded-2xl border border-slate-100 bg-white">
                  <h4 className="font-semibold text-slate-800 mb-3">Extracción AI</h4>
                  <pre className="text-xs text-slate-500 bg-slate-50 p-3 rounded-xl overflow-x-auto">
                    {JSON.stringify(job.extracted_features || { info: "No disponible" }, null, 2)}
                  </pre>
                </div>

                <div className="p-4 rounded-2xl border border-slate-100 bg-white">
                  <h4 className="font-semibold text-slate-800 mb-3">Evaluación de Riesgo</h4>
                  <pre className="text-xs text-slate-500 bg-slate-50 p-3 rounded-xl overflow-x-auto">
                    {JSON.stringify(job.risk_assessment || { info: "No disponible" }, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* Actions Bar */}
            <div className="sticky bottom-0 p-6 border-t border-slate-100 bg-white/90 backdrop-blur-md flex items-center justify-between">
              <p className="text-sm text-slate-400">Atajos: <kbd className="px-2 py-1 bg-slate-100 rounded text-slate-600">A</kbd> Aprobar <kbd className="px-2 py-1 bg-slate-100 rounded text-slate-600 ml-2">R</kbd> Rechazar</p>
              
              <div className="flex gap-3">
                <button 
                  onClick={() => onDecision(job.id, false)}
                  className="px-6 py-2.5 rounded-xl font-medium flex items-center gap-2 text-red-600 bg-red-50 hover:bg-red-100 transition-colors"
                >
                  <XCircle className="w-4 h-4" /> Rechazar
                </button>
                <button 
                  onClick={() => onDecision(job.id, true)}
                  className="px-6 py-2.5 rounded-xl font-medium flex items-center gap-2 text-white bg-emerald-500 hover:bg-emerald-600 transition-colors"
                >
                  <Check className="w-4 h-4" /> Aprobar
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Needed to make sure the AlertTriangle is correctly imported as I used it
import { AlertTriangle } from 'lucide-react';

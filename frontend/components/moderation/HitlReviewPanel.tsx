import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Check, XCircle, AlertTriangle, Loader2, ListTree } from 'lucide-react';
import type { Job } from '../../lib/hooks/useLiveJobs';

interface HitlReviewPanelProps {
  job: any | null; // job comes from Zustand state now
  onClose: () => void;
  // onDecision ya no es necesario pasarlo como prop desde page.tsx porque lo manejaremos aquí
}

export function HitlReviewPanel({ job, onClose }: HitlReviewPanelProps) {
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch Audit Trace when panel opens
  useEffect(() => {
    if (!job) return;
    
    setComment("");
    setError(null);
    setIsLoadingAudit(true);
    
    fetch(`/api/jobs/${job.id}/audit-trace`)
      .then(res => {
        if (!res.ok) throw new Error('No se pudo cargar la traza de auditoría');
        return res.json();
      })
      .then(data => {
        if (data.audit_log) setAuditLog(data.audit_log);
      })
      .catch(err => {
        console.error(err);
        // Fallback silencioso, puede no existir si falló el guardado previo
      })
      .finally(() => {
        setIsLoadingAudit(false);
      });
  }, [job]);

  // Handle Keyboard Shortcuts
  useEffect(() => {
    if (!job || isSubmitting) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Solo atajos si no estamos escribiendo en el textarea
      if (document.activeElement?.tagName === 'TEXTAREA') return;

      if (e.key.toLowerCase() === 'a' && comment.trim()) {
        handleDecision(true);
      } else if (e.key.toLowerCase() === 'r' && comment.trim()) {
        handleDecision(false);
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [job, comment, isSubmitting]);

  const handleDecision = async (approved: boolean) => {
    if (!comment.trim()) {
      setError("Debes ingresar una justificación obligatoria.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    
    try {
      const action = approved ? "Approve" : "Block"; // El grafo espera "Approve" o "Block" o "Reject" basado en tu lógica (asumimos Approve/Block)
      
      const res = await fetch(`/api/jobs/${job.id}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });

      if (!res.ok) throw new Error("Error al enviar la decisión al servidor.");
      
      // Close panel immediately to show fluid UI. Firebase will update in background
      onClose();
    } catch (err: any) {
      setError(err.message || "Error desconocido");
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {job && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-md"
          onClick={!isSubmitting ? onClose : undefined}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: -20, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-5xl max-h-[90vh] flex flex-col glass-panel rounded-3xl shadow-2xl bg-white/95"
          >
            {/* Header */}
            <div className="flex-none flex items-center justify-between p-6 border-b border-slate-100 bg-white/50 backdrop-blur-xl rounded-t-3xl">
              <div>
                <h2 className="text-xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  Revisión Manual Requerida
                </h2>
                <p className="text-sm text-slate-500 font-medium">Job ID: {job.id}</p>
              </div>
              <button 
                onClick={onClose}
                disabled={isSubmitting}
                className="p-2 rounded-full hover:bg-slate-100 transition-colors disabled:opacity-50"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
              
              {/* Left Column: Media & Product Details */}
              <div className="space-y-6">
                <div className="aspect-square rounded-3xl bg-slate-100 overflow-hidden border border-slate-200 relative group">
                  {job.gcs_image_uri ? (
                    <img 
                      src={job.gcs_image_uri.replace("gs://", "https://storage.googleapis.com/")} 
                      alt="Analizado" 
                      className="w-full h-full object-cover"
                      onError={(e) => { e.currentTarget.src = "https://placehold.co/600x600/e2e8f0/64748b?text=Image+Unavailable" }}
                    />
                  ) : (
                    <img 
                      src={"https://placehold.co/600x600/e2e8f0/64748b?text=Product+Image"} 
                      alt="Placeholder" 
                      className="w-full h-full object-cover mix-blend-multiply" 
                    />
                  )}
                </div>
                
                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-100">
                  <h3 className="font-semibold text-slate-800 text-lg mb-1">{job.title || 'Producto Sin Título'}</h3>
                  <p className="text-slate-600 text-sm leading-relaxed mb-3">{job.description || 'Sin Descripción'}</p>
                  <div className="inline-flex items-center px-3 py-1 rounded-lg bg-emerald-100/50 text-emerald-800 font-semibold text-sm">
                    ${job.price || 0} USD
                  </div>
                </div>
              </div>

              {/* Right Column: AI Analysis & Audit Log */}
              <div className="space-y-6 flex flex-col">
                
                {job.reasons && job.reasons.length > 0 && (
                  <div className="p-5 rounded-2xl bg-amber-50 border border-amber-100">
                    <h4 className="font-semibold text-amber-800 mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5" /> Motivos del Riesgo
                    </h4>
                    <ul className="space-y-2">
                      {job.reasons.map((r: string, i: number) => (
                        <li key={i} className="text-sm text-amber-700 flex gap-2 font-medium">
                          <span className="mt-0.5 opacity-50">•</span> {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Audit Trace View */}
                <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm flex-1">
                  <h4 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
                    <ListTree className="w-5 h-5 text-indigo-500" /> 
                    Trazabilidad de Nodos (Audit Log)
                  </h4>
                  
                  {isLoadingAudit ? (
                    <div className="flex items-center justify-center h-32">
                      <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                    </div>
                  ) : auditLog.length > 0 ? (
                    <div className="space-y-3 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                      {auditLog.map((log, i) => (
                        <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                          <div className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-white bg-indigo-100 text-indigo-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </div>
                          <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] p-3 rounded-xl border border-slate-100 bg-slate-50">
                            <p className="text-xs font-semibold text-slate-700 uppercase">{log.node}</p>
                            <p className="text-xs text-slate-500 mt-1">{log.message || "Completado exitosamente"}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400 text-center py-4">No hay traza de auditoría disponible.</p>
                  )}
                </div>

                {/* Comment Box */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">Justificación de la decisión <span className="text-rose-500">*</span></label>
                  <textarea 
                    value={comment}
                    onChange={e => setComment(e.target.value)}
                    placeholder="Escribe por qué apruebas o bloqueas este producto..."
                    className="w-full p-4 rounded-2xl bg-slate-50 border border-slate-200 text-sm outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-400 transition-all resize-none font-medium text-slate-800"
                    rows={3}
                    disabled={isSubmitting}
                  />
                  {error && <p className="text-xs text-rose-500 font-medium">{error}</p>}
                </div>

              </div>
            </div>

            {/* Actions Bar */}
            <div className="flex-none p-6 border-t border-slate-100 bg-white/80 backdrop-blur-xl rounded-b-3xl flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-sm text-slate-400 font-medium hidden sm:block">
                Atajos: <kbd className="px-2 py-1 bg-slate-100 rounded-md text-slate-600 border border-slate-200">A</kbd> Aprobar <kbd className="px-2 py-1 bg-slate-100 rounded-md text-slate-600 border border-slate-200 ml-1">R</kbd> Rechazar
              </p>
              
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <button 
                  onClick={() => handleDecision(false)}
                  disabled={isSubmitting || !comment.trim()}
                  className="flex-1 sm:flex-none px-6 py-3 rounded-2xl font-semibold flex items-center justify-center gap-2 text-rose-600 bg-rose-50 hover:bg-rose-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-5 h-5" />}
                  Bloquear
                </button>
                <button 
                  onClick={() => handleDecision(true)}
                  disabled={isSubmitting || !comment.trim()}
                  className="flex-1 sm:flex-none px-6 py-3 rounded-2xl font-semibold flex items-center justify-center gap-2 text-white bg-emerald-500 hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-5 h-5" />}
                  Aprobar
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

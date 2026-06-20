import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../../lib/store/useStore';
import { Loader2, ShieldCheck, AlertCircle, FileSearch, Fingerprint, Eye, Bot } from 'lucide-react';
import { ResultView } from '../ResultView';

interface ClientStatusViewProps {
  jobId: string;
}

const CONTEXT_CONFIG: Record<string, { text: string, icon: any, color: string, bg: string }> = {
  'analyzing_data': { text: 'Extrayendo características visuales', icon: Fingerprint, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  'reading_doc': { text: 'Buscando políticas en la base de datos', icon: FileSearch, color: 'text-blue-600', bg: 'bg-blue-50' },
  'checking_safety': { text: 'Analizando seguridad del contenido', icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  'evaluating_risk': { text: 'Evaluando riesgo de la publicación', icon: AlertCircle, color: 'text-amber-600', bg: 'bg-amber-50' },
  'generating_reasoning': { text: 'Generando justificación detallada', icon: Bot, color: 'text-purple-600', bg: 'bg-purple-50' },
  'pending_human_review': { text: 'En revisión manual por moderador', icon: Eye, color: 'text-rose-600', bg: 'bg-rose-50' },
  'human_review_completed': { text: 'Revisión manual completada', icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  'error_routing': { text: 'Error detectado, derivando a humano', icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
  'final_decision': { text: 'Decisión finalizada', icon: ShieldCheck, color: 'text-slate-600', bg: 'bg-slate-50' }
};

export function ClientStatusView({ jobId }: ClientStatusViewProps) {
  const { activeUiProjection, subscribeToActiveJobUI, isOnline } = useStore();
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    if (!jobId) return;
    const unsubscribe = subscribeToActiveJobUI(jobId);
    return () => unsubscribe();
  }, [jobId, subscribeToActiveJobUI]);

  useEffect(() => {
    if (activeUiProjection) {
      setHistory(prev => {
        const last = prev[prev.length - 1];
        if (!last || last.ui_context !== activeUiProjection.ui_context) {
          return [...prev, activeUiProjection];
        } else {
          const newHist = [...prev];
          newHist[newHist.length - 1] = activeUiProjection;
          return newHist;
        }
      });
    }
  }, [activeUiProjection]);

  // Si se pierde la conexión
  if (!isOnline) {
    return (
      <div className="flex items-center justify-center p-6 bg-slate-50 rounded-3xl border border-slate-200">
        <Loader2 className="w-5 h-5 text-slate-400 animate-spin mr-3" />
        <span className="text-slate-500 font-medium">Reconectando con el servidor...</span>
      </div>
    );
  }

  // Aún no hay datos en el historial
  if (history.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 bg-white/50 backdrop-blur-xl rounded-3xl border border-slate-100 shadow-sm">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mr-3" />
        <span className="text-indigo-900 font-medium">Iniciando análisis...</span>
      </div>
    );
  }

  const currentProjection = history[history.length - 1];
  const isFinal = currentProjection.status === 'APPROVE' || currentProjection.status === 'BLOCK' || currentProjection.status === 'COMPLETED';

  return (
    <motion.div 
      layout
      className={`relative overflow-hidden rounded-3xl border transition-colors duration-500 ${isFinal ? 'bg-white border-slate-200 shadow-lg' : 'bg-white/60 border-indigo-100 backdrop-blur-xl shadow-xl shadow-indigo-900/5'}`}
    >
      <div className="p-8 flex flex-col gap-4">
        <h3 className="text-xl font-bold text-slate-800 tracking-tight text-center mb-4">
          {isFinal ? (currentProjection.result?.final_action === 'Block' ? 'Producto Bloqueado' : 'Producto Aprobado') : 'Análisis en progreso...'}
        </h3>
        
        {isFinal && currentProjection.result ? (
          <ResultView result={currentProjection.result} />
        ) : (
          <div className="space-y-4">
            <AnimatePresence>
              {history.map((step, index) => {
                const config = CONTEXT_CONFIG[step.ui_context] || { text: step.ui_message, icon: Loader2, color: 'text-slate-600', bg: 'bg-slate-50' };
                const Icon = config.icon;
                const isCurrent = index === history.length - 1;
                const isStepFinal = step.status === 'APPROVE' || step.status === 'BLOCK' || step.status === 'COMPLETED';
                
                return (
                  <motion.div 
                    key={step.ui_context + index}
                    initial={{ opacity: 0, x: -20, height: 0 }}
                    animate={{ opacity: 1, x: 0, height: 'auto' }}
                    className={`flex items-center gap-4 p-4 rounded-2xl border ${isCurrent && !isFinal ? 'bg-white shadow-sm border-indigo-100' : 'bg-slate-50/50 border-transparent'}`}
                  >
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${config.bg}`}>
                      {step.ui_context === 'pending_human_review' ? (
                        <Eye className={`w-6 h-6 ${config.color} ${isCurrent ? 'animate-pulse' : ''}`} strokeWidth={1.5} />
                      ) : isStepFinal ? (
                        <ShieldCheck className={`w-6 h-6 ${step.result?.final_action === 'Block' ? 'text-red-500' : 'text-emerald-500'}`} strokeWidth={1.5} />
                      ) : (
                        <Icon className={`w-6 h-6 ${config.color} ${isCurrent ? 'animate-pulse' : ''}`} strokeWidth={1.5} />
                      )}
                    </div>
                    
                    <div className="flex-1">
                      <h4 className={`font-semibold text-sm ${isCurrent ? 'text-slate-800' : 'text-slate-500'}`}>
                        {isStepFinal ? (step.result?.final_action === 'Block' ? 'Bloqueado' : 'Aprobado') : config.text}
                      </h4>
                      <p className={`text-xs mt-1 ${isCurrent ? 'text-slate-500' : 'text-slate-400'}`}>
                        {isStepFinal ? (step.result?.reasoning ? step.result.reasoning : "Completado.") : step.ui_message}
                      </p>
                    </div>

                    {isCurrent && !isFinal && step.ui_context !== 'pending_human_review' && (
                      <Loader2 className="w-5 h-5 text-indigo-400 animate-spin shrink-0" />
                    )}
                    {!isCurrent && (
                      <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}

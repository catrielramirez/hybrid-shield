import { motion } from "framer-motion";
import { Clock, AlertCircle, Info, BookOpen, ShieldCheck } from "lucide-react";
import type { AnalysisResult } from "@/app/actions/analyze";
import { Separator } from "./Separator";
import { cn } from "@/lib/utils";

interface ResultViewProps {
  result: AnalysisResult;
  price?: number;
}

function RiskScoreBar({ score }: { score: number }) {
  // 0 -> Green, 0.5 -> Yellow, 1.0 -> Red
  const percentage = Math.round(score * 100);
  const colorClass = score < 0.3 ? "bg-emerald-500" : score < 0.7 ? "bg-amber-500" : "bg-red-500";
  
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-end">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Nivel de Riesgo</span>
        <span className={cn("text-xs font-black", score < 0.3 ? "text-emerald-600" : score < 0.7 ? "text-amber-600" : "text-red-600")}>
          {percentage}%
        </span>
      </div>
      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200/50">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className={cn("h-full transition-colors", colorClass)}
        />
      </div>
    </div>
  );
}

export function ResultView({ result }: ResultViewProps) {
  const isPending = result.status === "pending_human_review" || result.final_action === "Human Review";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="glass border border-white/70 rounded-2xl shadow-sm p-6 space-y-6"
    >
      {/* Header & Status */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Assessment Overview</h3>
          <p className="text-[11px] text-slate-500 font-medium">
            Agente Multi-Modal · LangGraph + Gemini 1.5 Flash
          </p>
        </div>
        
        {isPending ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700">
            <Clock className="w-3.5 h-3.5 animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-wider">Revisión Manual</span>
          </div>
        ) : (
          <div className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider",
            result.final_action === "Approve" ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-red-50 border-red-200 text-red-700"
          )}>
            {result.final_action === "Approve" ? <ShieldCheck className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            {result.final_action}
          </div>
        )}
      </div>

      <Separator />

      {/* Main Analysis Content */}
      <div className="space-y-5">
        {/* Risk Visual */}
        <RiskScoreBar score={result.risk_score} />

        {/* Reasoning Area */}
        <div className="bg-slate-50/50 border border-slate-100 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 text-slate-400">
            <Info className="w-3.5 h-3.5" />
            <span className="text-[10px] font-bold uppercase tracking-widest">Reasoning & Context</span>
          </div>
          <p className="text-xs leading-relaxed text-slate-600 font-medium italic">
            "{result.reasoning}"
          </p>
        </div>

        {/* Pending Banner */}
        {isPending && (
          <div className="p-3.5 rounded-xl bg-gradient-to-r from-amber-500/10 to-amber-500/5 border border-amber-500/20">
            <h4 className="text-[11px] font-bold text-amber-800 mb-1">Zona Gris Detectada</h4>
            <p className="text-[11px] text-amber-700/80 leading-snug">
              El producto presenta señales mixtas o una incertidumbre elevada ({Math.round((result.uncertainty || 0) * 100)}%). 
              Se requiere aprobación manual antes de ser listado.
            </p>
          </div>
        )}

        {/* Policy Citations */}
        {result.policy_citations && result.policy_citations.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-400">
              <BookOpen className="w-3.5 h-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-widest">Policy References</span>
            </div>
            <div className="grid grid-cols-1 gap-2.5">
              {result.policy_citations.map((cite, i) => (
                <div key={i} className="p-3 rounded-xl border border-slate-200 bg-white shadow-sm transition-all hover:border-indigo-200">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded uppercase">{cite.policy_id}</span>
                    <span className="text-[10px] font-bold text-slate-400">Relevancia: {Math.round(cite.relevance_score * 100)}%</span>
                  </div>
                  <h5 className="text-xs font-bold text-slate-800 mb-1.5">{cite.policy_title}</h5>
                  <div className="p-2 bg-slate-50 rounded-lg mb-2 text-[10px] text-slate-500 border-l-2 border-slate-200 font-medium italic leading-relaxed">
                    "{cite.snippet}"
                  </div>
                  <p className="text-[11px] text-slate-600 leading-normal">
                    <span className="font-bold text-slate-800">Aplicación:</span> {cite.reason}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Audit Trace - Minimalist */}
      {result.pipeline_steps && (
        <div className="pt-2">
          <Separator />
          <div className="mt-4 flex flex-wrap gap-2">
            {result.pipeline_steps.map((step: any, i) => (
              <span key={i} className={cn(
                "text-[9px] px-2 py-1 rounded-md border font-bold tracking-tight uppercase transition-all",
                step.status === "completed" ? "bg-emerald-50 border-emerald-100 text-emerald-600" : "bg-slate-50 border-slate-200 text-slate-400 opacity-50"
              )}>
                {step.node ? step.node.replace(/_/g, " ") : String(step).replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

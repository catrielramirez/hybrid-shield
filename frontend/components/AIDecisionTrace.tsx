"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ScanSearch,
  BookOpen,
  Radio,
  Calculator,
  Gavel,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Quote,
} from "lucide-react";
import type { AnalysisResult } from "@/app/actions/analyze";
import { cn } from "@/lib/utils";

/* ── Signal label map ── */
const SIGNAL_LABELS: Record<string, string> = {
  visual_dissonance: "Visual Dissonance",
  contact_info_detected: "Contact Info Detected",
  price_anomaly: "Price Anomaly",
  policy_match: "Policy Match",
};

/* ── Stage definitions ── */
interface Stage {
  id: string;
  label: string;
  icon: React.ElementType;
}

const STAGES: Stage[] = [
  { id: "extraction", label: "Feature Extraction", icon: ScanSearch },
  { id: "rag", label: "Policy Retrieval", icon: BookOpen },
  { id: "signals", label: "Signal Detection", icon: Radio },
  { id: "aggregation", label: "Risk Aggregation", icon: Calculator },
  { id: "decision", label: "Final Decision", icon: Gavel },
];

/* ── Stage status color ── */
function stageStatus(result: AnalysisResult, stageId: string) {
  if (stageId === "decision") {
    if (result.final_action === "Block") return "red";
    if (result.final_action === "Human Review") return "amber";
    return "green";
  }
  if (stageId === "signals") {
    const active = Object.values(result.signals).some(Boolean);
    return active ? "red" : "green";
  }
  if (stageId === "aggregation") {
    return result.risk_score >= 0.8 ? "red" : result.risk_score >= 0.4 ? "amber" : "green";
  }
  return "green";
}

const STATUS_COLORS = {
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
  grey: "bg-slate-300",
};

const STATUS_RING = {
  green: "ring-emerald-200",
  amber: "ring-amber-200",
  red: "ring-red-200",
  grey: "ring-slate-200",
};

/* ── Main Component ── */
export function AIDecisionTrace({ result }: { result: AnalysisResult }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggle = (id: string) => setExpanded((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-0">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-6 h-6 rounded-md bg-slate-900 flex items-center justify-center">
          <ScanSearch strokeWidth={1.5} className="w-3.5 h-3.5 text-white" />
        </div>
        <h3 className="text-sm font-semibold text-slate-800">AI Decision Trace</h3>
      </div>

      {STAGES.map((stage, idx) => {
        const status = stageStatus(result, stage.id);
        const isExpanded = expanded === stage.id;
        const isLast = idx === STAGES.length - 1;
        const Icon = stage.icon;

        return (
          <div key={stage.id} className="relative">
            {/* Timeline connector */}
            {!isLast && (
              <div
                className="absolute left-[15px] top-[36px] w-[2px] bg-slate-200"
                style={{ height: isExpanded ? "calc(100% - 18px)" : "24px" }}
              />
            )}

            {/* Node header */}
            <button
              onClick={() => toggle(stage.id)}
              className={cn(
                "w-full flex items-center gap-3 px-2 py-2 rounded-xl transition-all duration-200",
                "hover:bg-slate-50/80 text-left group"
              )}
            >
              {/* Status dot */}
              <div
                className={cn(
                  "relative z-10 w-[30px] h-[30px] rounded-full flex items-center justify-center ring-4",
                  STATUS_COLORS[status],
                  STATUS_RING[status]
                )}
              >
                <Icon strokeWidth={1.8} className="w-3.5 h-3.5 text-white" />
              </div>

              <div className="flex-1 min-w-0">
                <span className="text-xs font-semibold text-slate-700">{stage.label}</span>
              </div>

              <ChevronDown
                strokeWidth={1.5}
                className={cn(
                  "w-4 h-4 text-slate-400 transition-transform duration-200",
                  isExpanded && "rotate-180"
                )}
              />
            </button>

            {/* Expanded content */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="overflow-hidden"
                >
                  <div className="ml-[38px] mr-1 mb-3 mt-1 p-3.5 bg-slate-50/80 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-2.5">
                    <StageContent stage={stage.id} result={result} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}

/* ── Stage Content ── */
function StageContent({ stage, result }: { stage: string; result: AnalysisResult }) {
  switch (stage) {
    case "extraction":
      return <ExtractionContent result={result} />;
    case "rag":
      return <RAGContent result={result} />;
    case "signals":
      return <SignalsContent result={result} />;
    case "aggregation":
      return <AggregationContent result={result} />;
    case "decision":
      return <DecisionContent result={result} />;
    default:
      return null;
  }
}

/* ── Extraction ── */
function ExtractionContent({ result }: { result: AnalysisResult }) {
  const f = result.features;
  return (
    <>
      <Row label="Primary object" value={f.primary_object || "N/A"} />
      <Row label="Condition" value={f.product_condition || "N/A"} />
      <Row label="Image quality" value={f.image_quality || "N/A"} />
      {f.text_in_image && f.text_in_image.length > 0 && (
        <Row label="Text detected" value={f.text_in_image.join(", ")} />
      )}
      <div className="pt-1.5 space-y-1">
        <SignalPill label="Visual dissonance" active={!!f.visual_dissonance} />
        <SignalPill label="Contact info" active={!!f.contact_info_detected} />
        <SignalPill label="Condition issue" active={!!f.condition_issue_detected} />
      </div>
      {f.fraud_signals && f.fraud_signals.length > 0 && (
        <div className="mt-2 p-2 rounded bg-red-50/50 border border-red-100/50">
          <p className="text-[10px] uppercase font-bold text-red-700 mb-1">Fraud Signals</p>
          <div className="flex flex-wrap gap-1">
            {f.fraud_signals.map(s => (
              <span key={s} className="px-1.5 py-0.5 rounded bg-red-100 text-red-600 font-medium">{s}</span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

/* ── RAG ── */
function RAGContent({ result }: { result: AnalysisResult }) {
  const citations = result.policy_citations;
  if (!citations || citations.length === 0) {
    return <p className="text-slate-500 italic">No policies retrieved.</p>;
  }
  return (
    <div className="space-y-2.5">
      {citations.map((c) => (
        <div key={c.policy_id} className="space-y-1">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
              {c.policy_id}
            </span>
            <span className="font-medium text-slate-700">{c.policy_title}</span>
          </div>
          <div className="flex items-start gap-1.5 pl-0.5">
            <Quote strokeWidth={1.5} className="w-3 h-3 text-slate-400 mt-0.5 shrink-0" />
            <p className="text-slate-500 italic leading-relaxed">{c.snippet}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Signals ── */
function SignalsContent({ result }: { result: AnalysisResult }) {
  return (
    <div className="space-y-1.5">
      {Object.entries(result.signals).map(([key, active]) => (
        <SignalPill key={key} label={SIGNAL_LABELS[key] || key} active={active} />
      ))}
    </div>
  );
}

/* ── Aggregation ── */
function AggregationContent({ result }: { result: AnalysisResult }) {
  return (
    <div className="space-y-2.5">
      {(result.risk_breakdown || []).map((b) => (
        <div key={b.factor} className="space-y-0.5">
          <div className="flex justify-between">
            <span className="text-slate-600">{SIGNAL_LABELS[b.factor] || b.factor}</span>
            <span className="font-mono text-slate-700">+{b.weight.toFixed(2)}</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${b.weight * 100}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className={cn(
                "h-full rounded-full",
                b.weight >= 0.9 ? "bg-red-400" : b.weight >= 0.7 ? "bg-amber-400" : "bg-emerald-400"
              )}
            />
          </div>
        </div>
      ))}
      <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
        <span className="font-medium text-slate-700">Total Risk Score</span>
        <span
          className={cn(
            "font-mono font-bold text-sm",
            result.risk_score >= 0.8
              ? "text-red-600"
              : result.risk_score >= 0.4
              ? "text-amber-600"
              : "text-emerald-600"
          )}
        >
          {result.risk_score.toFixed(2)}
        </span>
      </div>

      {/* ── Model Confidence Card ── */}
      <div className="mt-4 p-3 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
        <h4 className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Model Confidence</h4>
        
        <div className="space-y-4">
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-slate-500">Confidence</span>
              <span className="font-mono font-bold text-slate-700">{(result.features.confidence || 0).toFixed(2)}</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden flex">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(result.features.confidence || 0) * 100}%` }}
                className="h-full bg-slate-400"
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-slate-500">Uncertainty</span>
              <span className="font-mono font-bold text-slate-700">{(result.uncertainty || 0).toFixed(2)}</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden flex">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(result.uncertainty || 0) * 100}%` }}
                className={cn("h-full", (result.uncertainty || 0) > 0.4 ? "bg-amber-400" : "bg-slate-300")}
              />
            </div>
          </div>
        </div>

        {(result.uncertainty || 0) > 0.4 && (
          <div className="mt-1 flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-amber-50 border border-amber-100/50">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span className="text-[10px] font-medium text-amber-700">
              Low model confidence – routed to human review.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Decision ── */
function DecisionContent({ result }: { result: AnalysisResult }) {
  const actionConfig = {
    Block: { icon: XCircle, color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
    "Human Review": { icon: AlertTriangle, color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200" },
    Approve: { icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200" },
  };
  const cfg = actionConfig[result.final_action];
  const ActionIcon = cfg.icon;

  return (
    <div className="space-y-2.5">
      <div className={cn("flex items-center gap-2 px-3 py-2 rounded-lg border", cfg.bg, cfg.border)}>
        <ActionIcon strokeWidth={1.5} className={cn("w-4 h-4", cfg.color)} />
        <span className={cn("font-semibold text-xs", cfg.color)}>{result.final_action.toUpperCase()}</span>
      </div>

      <p className="text-slate-600 leading-relaxed">{result.reasoning}</p>
      {result.policy_violations && result.policy_violations.length > 0 && (
        <div className="pt-1.5 space-y-1">
          <span className="font-medium text-slate-700">Policies Violated:</span>
          {result.policy_violations.map((v) => (
            <div key={v.policy_id + v.factor} className="flex items-start gap-1.5 pl-1">
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 shrink-0">
                {v.policy_id}
              </span>
              <span className="text-slate-500">{v.explanation}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Helpers ── */
function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-700 font-medium text-right">{value}</span>
    </div>
  );
}

function SignalPill({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-600">{label}</span>
      <span
        className={cn(
          "text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold",
          active
            ? "bg-red-100 text-red-700"
            : "bg-slate-100 text-slate-400"
        )}
      >
        {active ? "TRUE" : "FALSE"}
      </span>
    </div>
  );
}

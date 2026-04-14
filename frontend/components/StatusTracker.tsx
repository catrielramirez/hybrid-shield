"use client";

import { cn } from "@/lib/utils";
import { Check, Loader2 } from "lucide-react";

type Step = "generating_url" | "uploading" | "analyzing" | "done";

const STEPS: { key: Step; label: string }[] = [
  { key: "generating_url", label: "Generando URL segura" },
  { key: "uploading", label: "Subiendo imagen a Storage" },
  { key: "analyzing", label: "Iniciando análisis de IA" },
  { key: "done", label: "Decisión Lista" },
];

const stepOrder: Step[] = ["generating_url", "uploading", "analyzing", "done"];

interface StatusTrackerProps {
  currentStep: Step | "idle" | "error";
}

export function StatusTracker({ currentStep }: StatusTrackerProps) {
  const currentIndex = stepOrder.indexOf(currentStep as Step);

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STEPS.map((step, i) => {
        const isDone = currentIndex > i;
        const isActive = currentIndex === i;
        const isPending = currentIndex < i;

        return (
          <div key={step.key} className="flex items-center gap-1">
            <div className="flex items-center gap-1.5">
              <div
                className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center border text-xs transition-all duration-300",
                  isDone && "bg-slate-900 border-slate-900 text-white",
                  isActive && "border-slate-400 bg-white text-slate-600 animate-pulse",
                  isPending && "border-slate-200 bg-white text-slate-300"
                )}
              >
                {isDone ? (
                  <Check strokeWidth={2.5} className="w-3 h-3" />
                ) : isActive ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  "text-xs font-medium transition-colors duration-300",
                  isDone && "text-slate-600",
                  isActive && "text-slate-900",
                  isPending && "text-slate-300"
                )}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  "h-px w-6 transition-colors duration-500",
                  currentIndex > i ? "bg-slate-400" : "bg-slate-200"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

"use client";

import { cn } from "@/lib/utils";
import { AlertTriangle, BookOpen, Eye } from "lucide-react";

interface EvidenceSectionProps {
  reasoning: string;
  features: {
    primary_object_in_image?: string;
    text_in_image?: string[];
    dissonance_detected?: boolean;
    contact_info_detected?: boolean;
  };
  ragContext?: string;
}

export function EvidenceSection({ reasoning, features, ragContext }: EvidenceSectionProps) {
  const hasIssues = features.dissonance_detected || features.contact_info_detected;

  return (
    <div className="space-y-3">
      {/* Reasoning */}
      <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Eye strokeWidth={1.5} className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
            Análisis del Agente
          </span>
        </div>
        <p className="text-sm text-slate-700 leading-relaxed">{reasoning}</p>
      </div>

      {/* Detected anomalies */}
      {hasIssues && (
        <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle strokeWidth={1.5} className="w-4 h-4 text-amber-600" />
            <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">
              Anomalías Detectadas
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {features.dissonance_detected && (
              <span className="inline-flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-800 px-2.5 py-1 rounded-lg">
                Disonancia Visual
              </span>
            )}
            {features.contact_info_detected && (
              <span className="inline-flex items-center gap-1 text-xs font-medium bg-red-100 text-red-800 px-2.5 py-1 rounded-lg">
                Info de Contacto Prohibida
              </span>
            )}
          </div>
          {features.text_in_image && features.text_in_image.length > 0 && (
            <div className="mt-3 pt-3 border-t border-amber-100">
              <p className="text-xs text-amber-700 font-medium mb-1.5">Texto detectado en imagen:</p>
              <div className="flex flex-wrap gap-1.5">
                {features.text_in_image.map((t, i) => (
                  <code
                    key={i}
                    className="text-xs bg-white border border-amber-200 text-amber-900 px-2 py-0.5 rounded"
                  >
                    {t}
                  </code>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* RAG Policy context */}
      {ragContext && (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen strokeWidth={1.5} className="w-4 h-4 text-indigo-500" />
            <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">
              Política Violada (Vertex AI Search)
            </span>
          </div>
          <p className="text-sm text-indigo-800 leading-relaxed">{ragContext}</p>
        </div>
      )}
    </div>
  );
}

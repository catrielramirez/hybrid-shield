"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Shield } from "lucide-react";
import { AnalysisCard } from "@/components/AnalysisCard";
import { ResultView } from "@/components/ResultView";
import { SkeletonLoader } from "@/components/SkeletonLoader";
import type { AnalysisResult } from "@/app/actions/analyze";

export default function Home() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [price, setPrice] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);

  const handleResult = (res: AnalysisResult, p: number) => {
    setResult(res);
    setPrice(p);
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Subtle radial gradient background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(99,102,241,0.08) 0%, transparent 60%)",
        }}
      />

      {/* Header */}
      <header className="relative z-10 border-b border-slate-100 bg-white/70 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center">
              <Shield strokeWidth={1.5} className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-sm text-slate-900">Hybrid Shield</span>
            <span className="text-xs text-slate-400 font-normal hidden sm:inline">
              E-commerce Fraud Detection
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Agente activo
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-5xl mx-auto px-6 py-10">
        {/* Hero */}
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
            Moderación Inteligente
          </h1>
          <p className="mt-2 text-slate-500 text-sm max-w-md mx-auto">
            Detecta fraudes visuales, anomalías de precio y contenido prohibido alineado con las politicas de la empresa, con trazabilidad y auditabilidad usando IA multimodal y sistemas deterministas.
          </p>
        </div>

        {/* Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left: Input */}
          <div>
            <AnalysisCard
              onResult={(res, p) => {
                setIsLoading(true);
                handleResult(res, p);
              }}
            />
          </div>

          {/* Right: Result */}
          <div className="min-h-[200px]">
            <AnimatePresence mode="wait">
              {isLoading && !result ? (
                <SkeletonLoader key="skeleton" />
              ) : result ? (
                <ResultView key="result" result={result} price={price} />
              ) : (
                <div
                  key="placeholder"
                  className="flex flex-col items-center justify-center h-64 rounded-2xl border-2 border-dashed border-slate-200 text-slate-400"
                >
                  <Shield strokeWidth={1} className="w-10 h-10 mb-3 opacity-30" />
                  <p className="text-sm font-medium">Los resultados aparecerán aquí</p>
                  <p className="text-xs mt-1 opacity-70">
                    Ingresa un producto y presiona Analizar
                  </p>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Feature chips */}
        <div className="mt-10 flex flex-wrap justify-center gap-2">
          {[
            "Gemini 2.0 Flash Multimodal",
            "LangGraph Multi-Agent",
            "Vertex AI Search RAG",
            "Firestore Persistence",
          ].map((tag) => (
            <span
              key={tag}
              className="text-xs text-slate-500 bg-white border border-slate-200 px-3 py-1 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      </main>
    </div>
  );
}

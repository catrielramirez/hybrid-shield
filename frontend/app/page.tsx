"use client";

import { useState } from "react";
import { Shield, Type, AlignLeft, DollarSign } from "lucide-react";
import { DropzoneLiquid } from "@/components/moderation/DropzoneLiquid";
import { LiveStreamFeed } from "@/components/moderation/LiveStreamFeed";
import { HitlReviewPanel } from "@/components/moderation/HitlReviewPanel";
import { useLiveJobs } from "@/lib/hooks/useLiveJobs";
import type { Job } from "@/lib/hooks/useLiveJobs";
import { AnimatePresence } from "framer-motion";

export default function Home() {
  const { jobs, loading } = useLiveJobs();
  const [selectedHitlJob, setSelectedHitlJob] = useState<Job | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");

  const uploadToGCS = async (file: File) => {
    // Paso 1: Obtener URL
    const urlRes = await fetch("/api/get-upload-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || "image/jpeg",
      }),
    });
    if (!urlRes.ok) throw new Error("Error al inicializar la sesión de subida.");
    const { upload_url, job_id } = await urlRes.json();

    // Paso 2: Subida Binaria
    const uploadRes = await fetch(upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type || "image/jpeg" },
      body: file,
    });
    if (!uploadRes.ok) throw new Error("Error al subir la imagen a Google Cloud Storage.");

    // Paso 3: Notificar Metadatos
    const metaRes = await fetch("/api/metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id,
        filename: file.name,
        content_type: file.type || "image/jpeg",
        title: title || file.name,
        description: description || "Sin descripción proporcionada",
        price: parseFloat(price) || 0,
      }),
    });
    if (!metaRes.ok) throw new Error("Error al procesar los metadatos del producto.");

    return { job_id };
  };

  const handleFileDrop = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      await uploadToGCS(file);
      // Clean form after upload
      setTitle("");
      setDescription("");
      setPrice("");
    } catch (err: any) {
      setError(err.message || "Error al subir");
    } finally {
      setIsUploading(false);
    }
  };

  const handleHitlDecision = async (jobId: string, approved: boolean) => {
    // In a real app we would call a backend endpoint to resolve the HITL
    console.log(`Decision for ${jobId}: ${approved ? 'Approved' : 'Rejected'}`);
    
    // For this POC, just close the panel
    setSelectedHitlJob(null);
  };

  return (
    <div className="min-h-screen text-slate-800 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Background Gradient (Pure Light) */}
      <div 
        className="fixed inset-0 pointer-events-none z-0" 
        style={{
          background: "radial-gradient(ellipse at top right, rgba(238, 242, 255, 0.5), transparent 50%), radial-gradient(ellipse at bottom left, rgba(255, 255, 255, 0.8), transparent 50%)"
        }}
      />

      {/* Navbar */}
      <header className="sticky top-0 z-40 border-b border-black/5 bg-white/70 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-slate-900 flex items-center justify-center shadow-md">
              <Shield strokeWidth={1.5} className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-sm leading-tight text-slate-900">Hybrid Shield</h1>
              <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">AI Moderation</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100/50 text-[11px] font-medium text-emerald-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              Live Sync Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          
          {/* Left Column: Form & Upload */}
          <div className="lg:col-span-5 space-y-6">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 mb-2">Ingesta de Producto</h2>
              <p className="text-sm text-slate-500 leading-relaxed">
                Completa los metadatos y arrastra la imagen para iniciar el flujo de moderación multi-agente en tiempo real.
              </p>
            </div>

            <div className="glass-panel p-6 rounded-3xl space-y-4">
              <div className="relative group">
                <Type strokeWidth={1.5} className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Título del producto (Ej. Reloj Casio)"
                  className="w-full pl-11 pr-4 py-3 bg-white/50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-300 transition-all placeholder:text-slate-400 font-medium"
                />
              </div>

              <div className="relative group">
                <AlignLeft strokeWidth={1.5} className="absolute left-4 top-4 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Descripción detallada..."
                  rows={3}
                  className="w-full pl-11 pr-4 py-3 bg-white/50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-300 transition-all placeholder:text-slate-400 resize-none font-medium"
                />
              </div>

              <div className="relative group">
                <DollarSign strokeWidth={1.5} className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                <input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="Precio sugerido (USD)"
                  className="w-full pl-11 pr-4 py-3 bg-white/50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-300 transition-all placeholder:text-slate-400 font-medium"
                />
              </div>
            </div>

            <DropzoneLiquid 
              onFileDrop={handleFileDrop} 
              isUploading={isUploading} 
            />

            {error && (
              <div className="p-4 rounded-2xl bg-red-50 border border-red-100 text-red-600 text-sm font-medium">
                {error}
              </div>
            )}
          </div>

          {/* Right Column: Live Feed */}
          <div className="lg:col-span-7">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-xl font-bold tracking-tight text-slate-900">Live Stream</h2>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{jobs.length} Eventos</span>
            </div>
            <div className="relative min-h-[500px]">
              <LiveStreamFeed 
                jobs={jobs} 
                loading={loading} 
                onReviewClick={(job) => setSelectedHitlJob(job)} 
              />
            </div>
          </div>

        </div>
      </main>

      {/* Modals */}
      <HitlReviewPanel 
        job={selectedHitlJob} 
        onClose={() => setSelectedHitlJob(null)}
        onDecision={handleHitlDecision}
      />
    </div>
  );
}

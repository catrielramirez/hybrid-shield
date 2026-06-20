"use client";

import { useState, useEffect } from "react";
import { Shield, Type, AlignLeft, DollarSign, CheckCircle2, ShieldAlert, XCircle, ChevronRight, Sparkles } from "lucide-react";
import { DropzoneLiquid } from "@/components/moderation/DropzoneLiquid";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { analyzeProduct, type AnalysisResult } from "@/app/actions/analyze";
import { mockUpload } from "@/lib/mock/mockApiHandlers";

export default function Home() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [phase, setPhase] = useState<"IDLE" | "ANALYZING" | "RESULT">("IDLE");
  const [loadingStep, setLoadingStep] = useState<string>("");
  const [resultMock, setResultMock] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isFilling, setIsFilling] = useState(false);
  const [showClaimTooltip, setShowClaimTooltip] = useState(false);

  const uploadToGCS = async (
    file: File,
    metadata: { title: string; description: string; price: number }
  ): Promise<{ job_id: string }> => {
    // Use mock upload in mock mode
    if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
      return mockUpload({ file, metadata });
    }

    const strategy = process.env.NEXT_PUBLIC_STORAGE_STRATEGY || 'signed_url';
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || '';
    let job_id: string;

    if (strategy === 'local') {
      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await fetch(`${backendUrl}/api/upload-direct`, {
        method: "POST",
        body: formData,
      });
      if (!uploadRes.ok) throw new Error("Error al subir la imagen directamente.");
      const data = await uploadRes.json();
      job_id = data.job_id;
    } else {
      const urlRes = await fetch(`${backendUrl}/api/get-upload-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || "image/jpeg",
        }),
      });
      if (!urlRes.ok) {
        throw new Error(`Error al inicializar la sesión de subida.`);
      }
      const data = await urlRes.json();
      job_id = data.job_id;

      const uploadRes = await fetch(data.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "image/jpeg" },
        body: file,
      });
      if (!uploadRes.ok) throw new Error("Error al subir la imagen a Google Cloud Storage.");
    }

    const metaRes = await fetch(`${backendUrl}/api/metadata`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id,
        filename: file.name,
        content_type: file.type || "image/jpeg",
        title: metadata.title,
        description: metadata.description,
        price: metadata.price,
      }),
    });
    if (!metaRes.ok) throw new Error("Error al procesar los metadatos del producto.");

    return { job_id };
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;
    setError(null);
    setIsFilling(true);
    setPhase("ANALYZING");
    setLoadingStep("Iniciando análisis de riesgo...");

    try {
      const { job_id } = await uploadToGCS(selectedFile, {
        title,
        description,
        price: parseFloat(price) || 0,
      });

      // In mock mode, simulate state progression with visual updates
      if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
        const steps = [
          "Iniciando análisis de riesgo...",
          "Analizando imagen del producto...",
          "Consultando políticas de la plataforma...",
          "Generando decisión final...",
        ];

        // Variable delays between 2000-2700ms for more realistic feel
        // Last step is shorter to avoid feeling stuck
        const delays = [2100, 2400, 2300, 1800]; // Each step has different duration

        // Progress through steps with variable delays
        const progressSteps = async () => {
          for (let i = 0; i < steps.length; i++) {
            await new Promise(resolve => setTimeout(resolve, delays[i]));
            if (i + 1 < steps.length) {
              setLoadingStep(steps[i + 1]);
            }
          }
        };

        // Start the step progression
        const progressPromise = progressSteps();

        const { result, error: err } = await analyzeProduct({
          thread_id: job_id,
          gcs_uri: "",
          title,
          description,
          price: parseFloat(price) || 0,
        });

        // Wait for all steps to complete before showing result
        await progressPromise;

        if (err || !result) {
          throw new Error(err || "El análisis falló inesperadamente.");
        }

        setResultMock(result);
        setPhase("RESULT");
      } else {
        // Production mode - simple loading message
        setLoadingStep("Evaluando políticas de e-commerce...");

        const { result, error: err } = await analyzeProduct({
          thread_id: job_id,
          gcs_uri: "",
          title,
          description,
          price: parseFloat(price) || 0,
        });

        if (err || !result) {
          throw new Error(err || "El análisis falló inesperadamente.");
        }

        setResultMock(result);
        setPhase("RESULT");
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Error en el proceso de moderación.");
      setPhase("IDLE");
    } finally {
      setIsFilling(false);
    }
  };

  const handleReset = () => {
    setPhase("IDLE");
    setResultMock(null);
    setTitle("");
    setDescription("");
    setPrice("");
    setSelectedFile(null);
    setIsFilling(false);
    setShowClaimTooltip(false);
    setError(null);
  };

  return (
    <div className="min-h-screen text-slate-800 font-sans selection:bg-indigo-100 selection:text-indigo-900 bg-transparent flex flex-col overflow-x-hidden relative">
      {/* Fondo de imagen a pantalla completa */}
      <div className="fixed inset-0 pointer-events-none -z-10 bg-slate-900">
        <Image
          src="/background.png"
          alt="Background"
          fill
          priority
          quality={100}
          className="object-cover object-center opacity-100"
        />
        {/* Capa suave para que la imagen actúe como fondo sin distraer */}
        <div className="absolute inset-0 bg-white/40 backdrop-blur-[2px]" />
      </div>

      {/* Navbar */}
      <header className="sticky top-0 z-40 border-b border-black/5 bg-white/40 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-slate-900 flex items-center justify-center shadow-md">
              <Shield strokeWidth={1.5} className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-sm leading-tight text-slate-900">Hybrid Shield</h1>
              <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">AI Moderation</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/hitl" className="text-sm font-semibold text-slate-700 bg-white border border-slate-200 shadow-sm hover:shadow hover:bg-slate-50 px-4 py-2 rounded-xl flex items-center gap-1.5 transition-all">
              Employee Dashboard <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative z-10 flex items-center justify-center p-6 w-full max-w-6xl mx-auto">
        <div className="w-full flex items-center justify-center">
          <AnimatePresence mode="wait">

            {(phase === "IDLE" || phase === "ANALYZING") && (
              <motion.div
                layout
                key="main-stage"
                className={`w-full ${selectedFile && phase === 'IDLE' ? 'max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-10 items-center' : 'max-w-xl flex flex-col items-center justify-center'}`}
              >
                {/* Columna Izquierda / Centro: Dropzone */}
                <motion.div layout className="w-full flex flex-col items-center">
                  <AnimatePresence>
                    {!selectedFile && (
                      <motion.div
                        layout
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, height: 0, margin: 0 }}
                        className="text-center mb-8"
                      >
                        <h2 className="text-4xl font-bold tracking-tight text-slate-900 mb-3">Carga un producto</h2>
                        <p className="text-slate-700 font-semibold bg-white/50 backdrop-blur-md px-5 py-2 rounded-full inline-block border border-white/60 shadow-sm">
                          Nuestro sistema evaluará las políticas en tiempo real.
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <DropzoneLiquid
                    onFileDrop={(file) => setSelectedFile(file)}
                    selectedFile={selectedFile}
                    onClear={() => setSelectedFile(null)}
                    isUploading={phase === "ANALYZING"}
                    isCompact={!!selectedFile && phase === 'IDLE'}
                  />

                  {/* Textos de análisis bajo la imagen cuando está centrada */}
                  <AnimatePresence>
                    {phase === "ANALYZING" && (
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="mt-8 text-center bg-white/50 backdrop-blur-md px-8 py-4 rounded-3xl border border-white/60 shadow-sm inline-block"
                      >
                        <h3 className="text-2xl font-bold text-slate-900 mb-2">Analizando Producto</h3>
                        <p className="text-slate-700 font-semibold">{loadingStep}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* Columna Derecha: Formulario */}
                <AnimatePresence>
                  {selectedFile && phase === 'IDLE' && (
                    <motion.div
                      layout
                      initial={{ opacity: 0, x: 40, filter: 'blur(8px)' }}
                      animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                      exit={{ opacity: 0, scale: 0.95, filter: 'blur(10px)', position: 'absolute', right: '-100%' }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                      className="w-full space-y-6 flex flex-col"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-lg font-semibold text-slate-800">
                          Detalles del Producto
                        </h3>
                      </div>

                      <div className="relative rounded-[2rem] overflow-hidden p-[2px] shadow-[0_8px_30px_rgba(0,0,0,0.04)]">
                        {/* Borde animado (Luz perimetral) */}
                        <div className="absolute inset-[-100%] animate-[spin_4s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#e2e8f0_0%,#a5b4fc_50%,#e2e8f0_100%)] opacity-70" />

                        <div className="relative bg-white/90 backdrop-blur-xl p-6 rounded-[calc(2rem-2px)] space-y-5">

                          <div className="relative group">
                            <Type strokeWidth={1.5} className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-500 opacity-0 group-focus-within:opacity-100 blur-[2px] transition-opacity duration-300" />
                            <input
                              value={title}
                              onChange={(e) => setTitle(e.target.value)}
                              placeholder="Ej. Reloj Inteligente Serie 9 Pro"
                              className="w-full pl-11 pr-4 py-4 bg-slate-50/90 backdrop-blur-sm border border-slate-200 rounded-2xl text-sm outline-none transition-all placeholder:text-slate-400 font-medium relative z-10"
                            />
                          </div>

                          <div className="relative group">
                            <AlignLeft strokeWidth={1.5} className="absolute left-4 top-4 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-500 opacity-0 group-focus-within:opacity-100 blur-[2px] transition-opacity duration-300" />
                            <textarea
                              value={description}
                              onChange={(e) => setDescription(e.target.value)}
                              placeholder="Ej. Reloj inteligente de última generación con monitor de salud, resistente al agua..."
                              rows={4}
                              className="w-full pl-11 pr-4 py-4 bg-slate-50/90 backdrop-blur-sm border border-slate-200 rounded-2xl text-sm outline-none transition-all placeholder:text-slate-400 resize-none font-medium relative z-10"
                            />
                          </div>

                          <div className="relative group">
                            <DollarSign strokeWidth={1.5} className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
                            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-500 opacity-0 group-focus-within:opacity-100 blur-[2px] transition-opacity duration-300" />
                            <input
                              type="number"
                              value={price}
                              onChange={(e) => setPrice(e.target.value)}
                              placeholder="Ej. 299 (Precio sugerido en USD)"
                              className="w-full pl-11 pr-4 py-4 bg-slate-50/90 backdrop-blur-sm border border-slate-200 rounded-2xl text-sm outline-none transition-all placeholder:text-slate-400 font-medium relative z-10"
                            />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <button
                          onClick={handleStartAnalysis}
                          disabled={isFilling}
                          className="relative w-full py-5 rounded-[1.5rem] overflow-hidden bg-slate-900 text-white font-semibold shadow-[0_10px_30px_rgba(99,102,241,0.2)] hover:bg-slate-800 transition-all group disabled:opacity-70 disabled:cursor-not-allowed transform hover:scale-[1.02] active:scale-[0.98]"
                        >
                          {/* Efecto líquido llenando */}
                          <div
                            className={`absolute bottom-0 left-0 w-full bg-indigo-500 z-0 transition-all duration-[1800ms] ease-[cubic-bezier(0.4,0,0.2,1)] ${isFilling ? 'h-[120%]' : 'h-0'}`}
                            style={{
                              borderRadius: isFilling ? '0% 0% 100% 100%' : '50% 50% 0 0'
                            }}
                          />
                          <span className="relative z-10 flex items-center justify-center gap-2 text-base">
                            {isFilling ? "Inicializando Neural Engine..." : "Iniciar Evaluación"}
                          </span>
                        </button>

                        <div className="flex justify-center pt-2">
                          {error && (
                            <p className="text-xs font-medium text-rose-500 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2 text-center w-full">
                              {error}
                            </p>
                          )}
                        </div>
                      </div>

                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}

            {phase === "RESULT" && resultMock && (
              <motion.div
                key="result"
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                className="w-full max-w-xl"
              >
                <div className={`p-10 rounded-[24px] relative overflow-hidden bg-white/45 backdrop-blur-[16px] border border-white/40 transition-all duration-500 ${resultMock.final_action === 'Approve' ? 'shadow-[0_0_50px_rgba(16,185,129,0.2)]' :
                  resultMock.final_action === 'Block' ? 'shadow-[0_0_50px_rgba(244,63,94,0.2)]' :
                    'shadow-[0_0_50px_rgba(245,158,11,0.2)]'
                  }`}>
                  {/* Glow de fondo del card */}
                  <div className={`absolute top-0 left-0 w-full h-32 blur-3xl opacity-30 ${resultMock.final_action === 'Approve' ? 'bg-emerald-400' :
                    resultMock.final_action === 'Block' ? 'bg-rose-400' :
                      'bg-amber-400'
                    }`} />

                  <div className="flex items-center justify-center mb-8 relative z-10">
                    {resultMock.final_action === 'Approve' && (
                      <div className="w-20 h-20 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center shadow-inner">
                        <CheckCircle2 strokeWidth={1.5} className="w-10 h-10 text-emerald-500" />
                      </div>
                    )}
                    {resultMock.final_action === 'Block' && (
                      <div className="w-20 h-20 rounded-full bg-rose-50 border border-rose-100 flex items-center justify-center shadow-inner">
                        <XCircle strokeWidth={1.5} className="w-10 h-10 text-rose-500" />
                      </div>
                    )}
                    {resultMock.final_action === 'Human Review' && (
                      <div className="w-20 h-20 rounded-full bg-amber-50 border border-amber-100 flex items-center justify-center shadow-inner">
                        <ShieldAlert strokeWidth={1.5} className="w-10 h-10 text-amber-500" />
                      </div>
                    )}
                  </div>

                  <h3 className="text-3xl font-bold text-center text-slate-900 mb-4 relative z-10">
                    {resultMock.final_action === 'Approve' && '¡Producto Aprobado!'}
                    {resultMock.final_action === 'Block' && 'Producto Bloqueado'}
                    {resultMock.final_action === 'Human Review' && 'Revisión Requerida'}
                  </h3>

                  <div className="relative z-10">
                    {resultMock.final_action === 'Human Review' ? (
                      <p className="text-center text-slate-600 mb-10 font-medium text-lg leading-relaxed">
                        Necesitamos revisar tu caso. Nos comunicaremos contigo a la brevedad.
                      </p>
                    ) : resultMock.final_action === 'Block' ? (
                      <div className="bg-rose-50/80 backdrop-blur-sm rounded-3xl p-5 mb-8 border border-rose-100 shadow-sm">
                        <h4 className="font-semibold text-rose-900 mb-2 flex items-center gap-2">
                          <XCircle className="w-4 h-4 text-rose-500" /> Políticas infringidas
                        </h4>
                        <ul className="space-y-1.5 mb-4">
                          {resultMock.policy_violations?.map((v, i) => (
                            <li key={i} className="text-sm text-rose-700 bg-white/50 px-4 py-2.5 rounded-xl border border-rose-100/50">
                              {v.explanation}
                            </li>
                          ))}
                        </ul>
                        <h4 className="font-semibold text-rose-900 mb-1.5">Razonamiento de la IA</h4>
                        <p className="text-sm text-rose-700/90 leading-relaxed bg-white/50 p-3.5 rounded-xl border border-rose-100/50">
                          {resultMock.reasoning}
                        </p>
                      </div>
                    ) : (
                      <p className="text-center text-slate-600 mb-10 font-medium text-lg leading-relaxed">
                        Tu producto cumple con todas las normativas
                      </p>
                    )}
                  </div>

                  <div className="relative z-10 flex gap-3">
                    {resultMock.final_action === 'Block' && (
                      <div className="relative w-full">
                        <AnimatePresence>
                          {showClaimTooltip && (
                            <motion.div
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: 5 }}
                              className="absolute -top-12 left-0 right-0 mx-auto w-max px-3 py-1.5 bg-slate-800 text-white text-[11px] font-medium rounded-lg shadow-lg pointer-events-none"
                            >
                              Pronto tendrás esta herramienta
                              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45" />
                            </motion.div>
                          )}
                        </AnimatePresence>
                        <button
                          onClick={() => {
                            setShowClaimTooltip(true);
                            setTimeout(() => setShowClaimTooltip(false), 3000);
                          }}
                          className="w-full py-4 rounded-2xl text-sm font-semibold bg-rose-100 text-rose-700 hover:bg-rose-200 transition-all shadow-sm border border-rose-200 hover:-translate-y-0.5"
                        >
                          Generar reclamo
                        </button>
                      </div>
                    )}
                    <button
                      onClick={handleReset}
                      className="w-full py-4 rounded-2xl text-sm font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
                    >
                      Subir otro producto
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

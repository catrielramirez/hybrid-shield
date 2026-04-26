"use client";

import { useRef, useState, useCallback, useTransition } from "react";
import { Upload, X, DollarSign, Type, AlignLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { analyzeProduct, type AnalysisResult } from "@/app/actions/analyze";
import { StatusTracker } from "./StatusTracker";

type AnalysisStatus = 
  | "idle" 
  | "generating_url" 
  | "uploading" 
  | "analyzing" 
  | "done" 
  | "error";

interface AnalysisCardProps {
  onResult: (result: AnalysisResult, price: number) => void;
}

export function AnalysisCard({ onResult }: AnalysisCardProps) {
  const [isPending, startTransition] = useTransition();
  const [status, setStatus] = useState<AnalysisStatus>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const uploadToGCS = async (
    file: File,
    metadata: { title: string; description: string; price: number }
  ): Promise<{ job_id: string }> => {
    // Paso 1: Obtener URL
    setStatus("generating_url");
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
    setStatus("uploading");
    const uploadRes = await fetch(upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type || "image/jpeg" },
      body: file,
    });
    if (!uploadRes.ok) throw new Error("Error al subir la imagen a Google Cloud Storage.");

    // Paso 3: Notificar Metadatos
    // El backend persiste el JSON y dispara al Agente solo después de este paso.
    setStatus("analyzing");
    const metaRes = await fetch("/api/metadata", {
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

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    
    if (!imageFile) {
        setError("Por favor, selecciona una imagen del producto.");
        return;
    }

    const form = e.currentTarget;
    const formData = new FormData(form);
    const title = formData.get("title") as string;
    const description = formData.get("description") as string;
    const price = parseFloat(formData.get("price") as string) || 0;

    startTransition(async () => {
      try {
        // Fase de URL, Carga y Confirmación de Metadatos
        const { job_id } = await uploadToGCS(imageFile, { title, description, price });

        // Fase de Análisis (Trigger)
        const { result, error: err } = await analyzeProduct({
            thread_id: job_id,
            gcs_uri: "",  // Backend already knows the GCS path from metadata
            title,
            description,
            price
        });
        
        if (err || !result) {
          setStatus("error");
          setError(err ?? "El análisis falló inesperadamente.");
        } else {
          setStatus("done");
          onResult(result, price);
        }
      } catch (err: any) {
        setStatus("error");
        setError(err.message || "Error en el proceso de moderación.");
      }
    });
  };

  const isAnalyzing = isPending || (status !== "idle" && status !== "done" && status !== "error");

  return (
    <div className="glass border border-white/70 rounded-2xl shadow-sm p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-800">Analizar Producto</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Sube una imagen y describe el producto para comenzar el análisis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Dropzone */}
        <div
          className={cn(
            "relative border-2 border-dashed rounded-xl transition-all duration-200 overflow-hidden",
            dragOver ? "border-indigo-400 bg-indigo-50" : "border-slate-200 bg-slate-50/50",
            imagePreview ? "h-44" : "h-32"
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !imagePreview && fileInputRef.current?.click()}
        >
          {imagePreview ? (
            <div className="relative w-full h-full">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imagePreview}
                alt="Preview"
                className="w-full h-full object-cover"
              />
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setImageFile(null); setImagePreview(null); }}
                className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-full p-1 shadow-sm text-slate-600 hover:text-red-500 transition-colors"
              >
                <X strokeWidth={2} className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 cursor-pointer">
              <Upload strokeWidth={1.5} className="w-6 h-6 text-slate-400" />
              <span className="text-xs text-slate-500">
                Arrastra una imagen o <span className="text-indigo-500 font-medium">selecciona</span>
              </span>
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          name="image"
          accept="image/*"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />

        {/* Title */}
        <div className="relative">
          <Type strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            name="title"
            required
            type="text"
            placeholder="Título del producto"
            className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-slate-200 bg-white/80 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 transition"
          />
        </div>

        {/* Description */}
        <div className="relative">
          <AlignLeft strokeWidth={1.5} className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
          <textarea
            name="description"
            required
            placeholder="Descripción del producto..."
            rows={3}
            className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-slate-200 bg-white/80 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 transition resize-none"
          />
        </div>

        {/* Price */}
        <div className="relative">
          <DollarSign strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            name="price"
            type="number"
            step="0.01"
            min="0"
            placeholder="Precio (USD)"
            className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-slate-200 bg-white/80 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 transition"
          />
        </div>

        {/* Status tracker */}
        {isAnalyzing && (
          <div className="pt-1">
            <StatusTracker currentStep={status as "generating_url" | "uploading" | "analyzing" | "done"} />
          </div>
        )}

        {/* Error */}
        {error && (
          <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isAnalyzing}
          className={cn(
            "w-full py-2.5 px-4 rounded-xl text-sm font-semibold transition-all duration-200",
            isAnalyzing
              ? "bg-slate-100 text-slate-400 cursor-not-allowed"
              : "bg-slate-900 text-white hover:bg-slate-700 active:scale-[0.99]"
          )}
        >
          {isAnalyzing ? "Analizando..." : "Analizar con Semantic Shield"}
        </button>
      </form>
    </div>
  );
}

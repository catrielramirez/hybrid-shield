import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, X } from 'lucide-react';

interface DropzoneLiquidProps {
  onFileDrop: (file: File) => void;
  isUploading?: boolean;
  selectedFile?: File | null;
  onClear?: () => void;
  isCompact?: boolean; // Prop para ajustar tamaño cuando esté en la columna izquierda
}

export function DropzoneLiquid({ onFileDrop, isUploading = false, selectedFile, onClear, isCompact = false }: DropzoneLiquidProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (selectedFile) {
      const objectUrl = URL.createObjectURL(selectedFile);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreview(objectUrl);
      return () => URL.revokeObjectURL(objectUrl);
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreview(null);
    }
  }, [selectedFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileDrop(e.dataTransfer.files[0]);
    }
  }, [onFileDrop]);

  return (
    <motion.div
      layout
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative w-full ${isCompact ? 'max-w-full' : 'max-w-xl mx-auto'} rounded-[24px] overflow-hidden group transition-all duration-500 backdrop-blur-[16px] ${
        preview
          ? 'bg-white/45 border border-white/40 shadow-[0_0_50px_rgba(99,102,241,0.2)]'
          : isDragActive
            ? 'bg-white/55 border border-indigo-400/60 shadow-[0_0_60px_rgba(99,102,241,0.4)]'
            : 'bg-white/45 border border-white/40 shadow-[0_0_40px_rgba(99,102,241,0.15)] hover:bg-white/50 hover:border-indigo-300/60 hover:shadow-[0_0_50px_rgba(99,102,241,0.35)]'
      }`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ 
        opacity: 1, 
        scale: isDragActive ? 1.02 : 1,
      }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
    >
      
      {/* Hidden File Input */}
      <input 
        id="file-upload" 
        type="file" 
        className="hidden" 
        accept="image/*"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            onFileDrop(e.target.files[0]);
          }
          e.target.value = '';
        }}
      />

      <AnimatePresence mode="wait">
        {preview ? (
          <motion.div
            key="preview"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={`relative w-full ${isCompact ? 'h-[500px]' : 'h-80'} flex items-center justify-center bg-slate-100/50 z-10 overflow-hidden`}
          >
            {/* Efecto Glow/Aura trasero */}
            <div className="absolute inset-4 bg-indigo-400/30 blur-[40px] rounded-full z-0 mix-blend-multiply" />
            
            <motion.img 
              layoutId="uploaded-image"
              src={preview} 
              alt="Preview" 
              className="w-full h-full object-cover z-10 relative" 
            />

            {/* Efecto de escaneo inicial (Un solo pase) */}
            {!isUploading && (
              <motion.div
                initial={{ top: '-10%', opacity: 0 }}
                animate={{ top: '110%', opacity: [0, 1, 1, 0] }}
                transition={{ duration: 2.5, ease: "easeInOut", delay: 0.2 }}
                className="absolute left-0 right-0 h-32 bg-gradient-to-b from-transparent via-blue-800/40 to-blue-900/80 z-20 pointer-events-none blur-sm border-b border-blue-600"
              />
            )}

            {/* Overlay de Análisis durante 'isUploading' */}
            <AnimatePresence>
              {isUploading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm z-30 flex flex-col items-center justify-center"
                >
                  {/* Escáner constante y misterioso */}
                  <motion.div 
                    animate={{ top: ['0%', '100%', '0%'] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                    className="absolute left-0 right-0 h-1 bg-blue-600 shadow-[0_0_15px_3px_rgba(37,99,235,0.8)] z-40"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {!isUploading && (
              <button
                onClick={(e) => { e.stopPropagation(); onClear?.(); }}
                className="absolute top-4 right-4 bg-white/80 backdrop-blur-md rounded-full p-2 shadow-lg text-slate-600 hover:text-red-500 hover:bg-white transition-all z-40 border border-white/50"
              >
                <X strokeWidth={2.5} className="w-4 h-4" />
              </button>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={`flex flex-col items-center justify-center ${isCompact ? 'h-[500px]' : 'p-16 h-80'} text-center cursor-pointer relative z-10`}
            onClick={() => document.getElementById('file-upload')?.click()}
          >
            <motion.div 
              animate={{ y: [0, -4, 0] }} 
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="mb-6 flex items-center justify-center relative"
            >
              <svg width="0" height="0" className="absolute">
                <defs>
                  <linearGradient id="cloud-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop stopColor="#8b5cf6" offset="0%" />
                    <stop stopColor="#6366f1" offset="100%" />
                  </linearGradient>
                </defs>
              </svg>
              <UploadCloud strokeWidth={1.5} className="w-14 h-14" style={{ stroke: "url(#cloud-gradient)", filter: "drop-shadow(0px 4px 6px rgba(99, 102, 241, 0.2))" }} />
            </motion.div>
            <h3 className="text-slate-800 font-[500] text-2xl tracking-tight mb-2">
              Arrastra una imagen
            </h3>
            <div className="flex flex-col items-center mt-6">
              <div className="px-6 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-md shadow-indigo-600/20 transition-all mb-3">
                O haz clic para explorar
              </div>
              <p className="text-slate-500 text-[11px] font-medium tracking-wide">
                JPG, PNG, PDF · máx 10MB
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

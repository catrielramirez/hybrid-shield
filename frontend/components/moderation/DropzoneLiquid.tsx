import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, CheckCircle2, ShieldAlert } from 'lucide-react';

interface DropzoneLiquidProps {
  onFileDrop: (file: File) => void;
  isUploading?: boolean;
}

export function DropzoneLiquid({ onFileDrop, isUploading = false }: DropzoneLiquidProps) {
  const [isDragActive, setIsDragActive] = useState(false);

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
      className="relative w-full max-w-lg mx-auto rounded-3xl overflow-hidden glass-panel"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ 
        opacity: 1, 
        scale: isDragActive ? 1.02 : 1,
        borderColor: isDragActive ? 'rgba(99,102,241, 0.4)' : 'var(--color-border-subtle)'
      }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      style={{
        boxShadow: isDragActive ? '0 10px 40px rgba(99,102,241, 0.1)' : '0 4px 30px rgba(0,0,0, 0.02)'
      }}
    >
      <div className="absolute inset-0 z-0 pointer-events-none bg-gradient-to-b from-transparent to-slate-50/50" />
      
      <AnimatePresence mode="wait">
        {isUploading ? (
          <motion.div
            key="uploading"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex flex-col items-center justify-center p-12 text-center relative z-10"
          >
            <div className="w-16 h-16 mb-4 relative flex items-center justify-center">
              <motion.div 
                className="absolute inset-0 rounded-full border-2 border-indigo-100"
              />
              <motion.div 
                className="absolute inset-0 rounded-full border-2 border-indigo-500 border-t-transparent"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              />
              <UploadCloud className="w-6 h-6 text-indigo-500" />
            </div>
            <h3 className="text-slate-700 font-medium text-lg">Iniciando Análisis</h3>
            <p className="text-slate-400 text-sm mt-1">Conectando con Neural Engine...</p>
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center p-12 text-center cursor-pointer relative z-10"
            onClick={() => document.getElementById('file-upload')?.click()}
          >
            <motion.div 
              animate={{ y: [0, -5, 0] }} 
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 shadow-inner"
            >
              <UploadCloud className="w-8 h-8 text-indigo-400" />
            </motion.div>
            <h3 className="text-slate-800 font-medium text-xl">Arrastra una imagen</h3>
            <p className="text-slate-400 text-sm mt-2 max-w-xs">
              Sube el producto para iniciar la evaluación con el motor multi-agente
            </p>
            <input 
              id="file-upload" 
              type="file" 
              className="hidden" 
              accept="image/*"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  onFileDrop(e.target.files[0]);
                }
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

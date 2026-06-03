import { motion } from 'framer-motion';

interface LangGraphVisualizerProps {
  status: string; // PENDING, EXTRACTOR, RAG, DECISION, Needs Review, Done, ERROR
}

const NODES = [
  { id: 'PRE_FILTER', label: 'Pre-Filtro' },
  { id: 'EXTRACTOR', label: 'Extractor' },
  { id: 'RAG', label: 'Context RAG' },
  { id: 'DECISION', label: 'Motor Decisión' }
];

export function LangGraphVisualizer({ status }: LangGraphVisualizerProps) {
  // Simple mapping to active node index
  const getActiveIndex = () => {
    switch (status) {
      case 'PENDING': return 0;
      case 'EXTRACTOR': return 1;
      case 'RAG': return 2;
      case 'DECISION': return 3;
      case 'Needs Review': 
      case 'Done':
      case 'ERROR': return 4; // Completed all those
      default: return 0;
    }
  };

  const activeIndex = getActiveIndex();

  return (
    <div className="flex items-center justify-between w-full py-4 relative">
      {/* Background Track */}
      <div className="absolute top-1/2 left-0 w-full h-[2px] bg-slate-100 -translate-y-1/2 z-0" />
      
      {/* Active Track (Animated) */}
      <motion.div 
        className="absolute top-1/2 left-0 h-[2px] bg-indigo-200 -translate-y-1/2 z-0"
        initial={{ width: '0%' }}
        animate={{ width: `${Math.min((activeIndex / (NODES.length - 1)) * 100, 100)}%` }}
        transition={{ type: "spring", stiffness: 100, damping: 20 }}
      />

      {/* Nodes */}
      {NODES.map((node, idx) => {
        const isActive = idx === activeIndex;
        const isPast = idx < activeIndex;

        return (
          <div key={node.id} className="relative z-10 flex flex-col items-center">
            <motion.div
              layout
              className={`w-4 h-4 rounded-full flex items-center justify-center border-2 transition-colors duration-500`}
              animate={{
                backgroundColor: isActive ? '#fff' : isPast ? '#E0E7FF' : '#fff',
                borderColor: isActive ? '#6366F1' : isPast ? '#A5B4FC' : '#E2E8F0',
                scale: isActive ? 1.2 : 1
              }}
              style={{
                boxShadow: isActive ? '0 0 15px rgba(99,102,241, 0.4)' : 'none'
              }}
            >
              {isActive && (
                <motion.div 
                  className="w-1.5 h-1.5 rounded-full bg-indigo-500"
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              )}
            </motion.div>
            <span className={`text-[10px] mt-2 font-medium transition-colors duration-300 ${isActive ? 'text-indigo-600' : isPast ? 'text-slate-500' : 'text-slate-300'}`}>
              {node.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

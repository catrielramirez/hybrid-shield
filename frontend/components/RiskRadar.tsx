"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface RiskBarProps {
  label: string;
  value: number; // 0 to 1
  color: string;
  delay?: number;
}

function RiskBar({ label, value, color, delay = 0 }: RiskBarProps) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-slate-600">{label}</span>
        <span className={cn("text-xs font-semibold tabular-nums", color)}>{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full", color.replace("text-", "bg-"))}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, delay, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

interface RiskRadarProps {
  riskScore: number;
  features: {
    dissonance_detected?: boolean;
    contact_info_detected?: boolean;
  };
  price?: number;
}

export function RiskRadar({ riskScore, features, price }: RiskRadarProps) {
  // Derive individual axis scores from available signal
  const priceRisk = price != null && price < 10 ? 0.9 : price != null && price < 50 ? 0.5 : 0.1;
  const contentRisk = features.contact_info_detected ? 0.95 : features.dissonance_detected ? 0.7 : 0.1;
  const legitimacyRisk = riskScore;

  const getColor = (v: number) =>
    v >= 0.7 ? "text-red-500" : v >= 0.4 ? "text-amber-500" : "text-emerald-500";

  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4 space-y-3">
      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
        Dimensiones de Riesgo
      </h4>
      <RiskBar
        label="Anomalía de Precio"
        value={priceRisk}
        color={getColor(priceRisk)}
        delay={0}
      />
      <RiskBar
        label="Riesgo de Contenido"
        value={contentRisk}
        color={getColor(contentRisk)}
        delay={0.1}
      />
      <RiskBar
        label="Legitimidad General"
        value={legitimacyRisk}
        color={getColor(legitimacyRisk)}
        delay={0.2}
      />
    </div>
  );
}

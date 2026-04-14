"use client";

import { cn } from "@/lib/utils";
import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

type ActionType = "Approve" | "Human Review" | "Block";

interface RiskBadgeProps {
  action: ActionType;
  score: number;
}

const config: Record<
  ActionType,
  { label: string; bg: string; border: string; text: string; icon: React.ReactNode }
> = {
  Approve: {
    label: "Approved",
    bg: "bg-emerald-50/80",
    border: "border-emerald-200",
    text: "text-emerald-700",
    icon: <ShieldCheck strokeWidth={1.5} className="w-5 h-5" />,
  },
  "Human Review": {
    label: "Human Review",
    bg: "bg-amber-50/80",
    border: "border-amber-200",
    text: "text-amber-700",
    icon: <ShieldQuestion strokeWidth={1.5} className="w-5 h-5" />,
  },
  Block: {
    label: "Blocked",
    bg: "bg-red-50/80",
    border: "border-red-200",
    text: "text-red-700",
    icon: <ShieldAlert strokeWidth={1.5} className="w-5 h-5" />,
  },
};

export function RiskBadge({ action, score }: RiskBadgeProps) {
  const c = config[action];
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2.5 px-4 py-2.5 rounded-2xl border backdrop-blur-sm",
        c.bg,
        c.border,
        c.text
      )}
    >
      {c.icon}
      <div className="flex flex-col">
        <span className="font-semibold text-sm leading-tight">{c.label}</span>
        <span className="text-xs font-normal opacity-70">
          Risk Score: {(score * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

"use client";

export function SkeletonLoader() {
  return (
    <div className="glass border border-white/70 rounded-2xl shadow-sm p-5 space-y-4 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="space-y-1.5">
          <div className="h-3.5 w-40 bg-slate-200 rounded" />
          <div className="h-2.5 w-56 bg-slate-100 rounded" />
        </div>
        <div className="h-9 w-28 bg-slate-200 rounded-xl" />
      </div>
      <div className="h-px bg-slate-100" />
      <div className="space-y-3">
        <div className="h-2.5 w-32 bg-slate-100 rounded" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between">
              <div className="h-2.5 w-24 bg-slate-100 rounded" />
              <div className="h-2.5 w-8 bg-slate-100 rounded" />
            </div>
            <div className="h-1.5 w-full bg-slate-100 rounded-full" />
          </div>
        ))}
      </div>
      <div className="h-px bg-slate-100" />
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-2.5 bg-slate-100 rounded" style={{ width: `${100 - i * 10}%` }} />
        ))}
      </div>
    </div>
  );
}

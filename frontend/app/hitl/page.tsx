"use client";

import { useState } from "react";
import { Shield, ChevronLeft, Search, CheckCircle2, ShieldAlert, XCircle, ListTree, Check, X, Clock, ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect } from "react";
import Link from "next/link";
import { collection, query, where, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { mockGetTrace, mockSubmitDecision, mockGetImageUrl } from "@/lib/mock/mockApiHandlers";
import { MOCK_JOBS } from "@/lib/mock/mockData";

export default function HitlDashboard() {
  const [activeTab, setActiveTab] = useState<"PENDING" | "HISTORY">("PENDING");
  const [selectedJob, setSelectedJob] = useState<any | null>(null);
  const [pendingJobs, setPendingJobs] = useState<any[]>([]);
  const [historicalJobs, setHistoricalJobs] = useState<any[]>([]);

  // Accordion state for trace view
  const [expandedNodeIndex, setExpandedNodeIndex] = useState<number | null>(null);
  const [traceData, setTraceData] = useState<any>(null);
  const [isLoadingTrace, setIsLoadingTrace] = useState(false);
  const [justification, setJustification] = useState("");

  // Paginación para historial
  const [historyLimit, setHistoryLimit] = useState(10);

  // Helper para normalizar fechas (Firestore Timestamp o ISO String)
  const getMillis = (dateObj: any) => {
    if (!dateObj) return 0;
    if (typeof dateObj.toMillis === 'function') return dateObj.toMillis();
    if (typeof dateObj.toDate === 'function') return dateObj.toDate().getTime();
    if (dateObj.seconds) return dateObj.seconds * 1000;
    const time = new Date(dateObj).getTime();
    return isNaN(time) ? 0 : time;
  };

  useEffect(() => {
    // Debug: log the environment variable
    console.log('[HITL] NEXT_PUBLIC_DATA_SOURCE:', process.env.NEXT_PUBLIC_DATA_SOURCE);
    
    // Check if we're in mock mode using the isMockMode flag from firebase.ts
    const isMock = process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock';
    console.log('[HITL] Is mock mode:', isMock);
    
    // Use mock data in mock mode
    if (isMock) {
      console.log('[HITL] Loading mock data...');
      // Filter pending jobs (HUMAN_REVIEW status)
      const pending = MOCK_JOBS.filter(j => 
        j.status === 'PENDING_HUMAN_REVIEW' || j.final_action === 'Human Review'
      );
      console.log('[HITL] Mock pending jobs:', pending.length, pending.map(j => j.id));
      setPendingJobs(pending);

      // Filter historical jobs (APPROVE, BLOCK, etc.)
      const historical = MOCK_JOBS.filter(j => 
        j.status === 'APPROVE' || j.status === 'BLOCK' || 
        j.final_action === 'Approve' || j.final_action === 'Block'
      );
      console.log('[HITL] Mock historical jobs:', historical.length);
      setHistoricalJobs(historical);
      
      return; // Skip Firestore listeners
    }

    console.log('[HITL] Loading from Firestore...');
    // Listener para PENDIENTES (Strictly HITL pending reviews)
    const qPending = query(
      collection(db, "jobs"),
      where("status", "==", "PENDING_HUMAN_REVIEW")
    );

    const unsubPending = onSnapshot(qPending, (snapshot) => {
      const jobs = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      // Ordenamiento en memoria para evitar el error de índice compuesto en Firebase durante dev
      jobs.sort((a: any, b: any) => {
        const valA = getMillis(a.created_at || a.timestamp || a.last_update);
        const valB = getMillis(b.created_at || b.timestamp || b.last_update);
        return valB - valA;
      });
      setPendingJobs(jobs);
    });

    // Listener para HISTORIAL
    const qHistory = query(
      collection(db, "jobs"),
      where("status", "in", ["APPROVE", "BLOCK", "MANUAL_REVIEW", "COMPLETED", "APPROVED", "REJECTED", "FAILED", "ERROR"])
    );

    const unsubHistory = onSnapshot(qHistory, (snapshot) => {
      const jobs = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      // Ordenamiento en memoria
      jobs.sort((a: any, b: any) => {
        const valA = getMillis(a.last_update || a.created_at || a.timestamp);
        const valB = getMillis(b.last_update || b.created_at || b.timestamp);
        return valB - valA;
      });
      setHistoricalJobs(jobs);
    });

    return () => {
      unsubPending();
      unsubHistory();
    };
  }, []);

  const handleSelectJob = async (job: any) => {
    setSelectedJob(job);
    setExpandedNodeIndex(null);
    setTraceData(null);

    // Disparar carga forense
    setIsLoadingTrace(true);
    try {
      // Use mock handler in mock mode
      if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
        const data = await mockGetTrace(job.thread_id || job.id);
        // Invertimos la traza para lectura cronológica
        if (data.trace && Array.isArray(data.trace)) {
          data.trace = [...data.trace].reverse();
        }
        setTraceData(data);
      } else {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${backendUrl}/api/audit/trace/${job.thread_id || job.id}`);
        if (res.ok) {
          const data = await res.json();
          // Invertimos la traza (el backend devuelve del más reciente al más antiguo)
          // para que en la UI se lea cronológicamente (de arriba hacia abajo).
          if (data.trace && Array.isArray(data.trace)) {
            data.trace = [...data.trace].reverse();
          }
          setTraceData(data);
        }
      }
    } catch (err) {
      console.error("Error fetching trace:", err);
    } finally {
      setIsLoadingTrace(false);
    }
  };

  const handleDecision = async (final_action: 'Approve' | 'Block') => {
    if (!selectedJob) return;
    const jobId = selectedJob.thread_id || selectedJob.id;
    try {
      // Use mock handler in mock mode
      if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
        await mockSubmitDecision(jobId, final_action);
        
        // Update the job status and move to historical
        const updatedJob = {
          ...selectedJob,
          status: final_action.toUpperCase(),
          final_action: final_action,
          last_update: new Date().toISOString()
        };
        
        // Remove from pending
        setPendingJobs(prev => prev.filter(j => (j.thread_id || j.id) !== jobId));
        
        // Add to historical
        setHistoricalJobs(prev => [updatedJob, ...prev]);
        
        // Clear selection
        setSelectedJob(null);
        setJustification("");
      } else {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${backendUrl}/api/jobs/${jobId}/resume`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ action: final_action, justification })
        });
        if (res.ok) {
          setExpandedNodeIndex(null);
          // Optimistic live update: instantly remove from pending list and clear selection
          setPendingJobs(prev => prev.filter(j => (j.thread_id || j.id) !== jobId));
          setSelectedJob(null);
          setJustification(""); // Clear text
        } else {
          alert("Error al guardar la decisión.");
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getImageUrl = (job: any) => {
    if (!job) return "https://placehold.co/400x400/f8fafc/94a3b8?text=No+Image";
    
    // Use mock handler in mock mode
    if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
      return mockGetImageUrl(job.thread_id || job.id);
    }
    
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return `${backendUrl}/api/jobs/${job.thread_id || job.id}/image`;
  };

  const formatDate = (dateObj: any) => {
    if (!dateObj) return "N/A";
    let d: Date;
    if (typeof dateObj.toDate === 'function') {
      d = dateObj.toDate();
    } else if (dateObj.seconds) {
      d = new Date(dateObj.seconds * 1000);
    } else {
      d = new Date(dateObj);
    }

    if (isNaN(d.getTime())) return "Fecha inválida";

    return d.toLocaleString("es-ES", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
    });
  };

  const getJobField = (job: any, field: string) => job?.[field] ?? job?.input_data?.[field] ?? job?.metadata?.[field];

  const getStatusBadge = (status: string) => {
    const s = (status || "").toUpperCase();
    if (s === 'APPROVE' || s === 'APPROVED') return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200"><CheckCircle2 className="w-3.5 h-3.5" /> Aprobado</span>;
    if (s === 'BLOCK' || s === 'BLOCKED') return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-50 text-rose-700 text-xs font-semibold border border-rose-200"><XCircle className="w-3.5 h-3.5" /> Bloqueado</span>;
    return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-50 text-amber-700 text-xs font-semibold border border-amber-200"><ShieldAlert className="w-3.5 h-3.5" /> Pendiente</span>;
  };

  const getNodeStatusBadge = (status: string) => {
    if (status === 'completed') return <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold uppercase">Completed</span>;
    if (status === 'error') return <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 text-[10px] font-bold uppercase">Error</span>;
    return <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold uppercase">Pending</span>;
  };

  const getSignalColor = (signal: string) => {
    const dangerSignals = ['banned_object', 'external_contact', 'contact_info_detected'];
    const warningSignals = ['price_anomaly', 'visual_dissonance', 'stock_photo_detected', 'condition_issue', 'unverifiable_image'];

    if (dangerSignals.includes(signal)) return "bg-rose-50 text-rose-700 border-rose-200";
    if (warningSignals.includes(signal)) return "bg-amber-50 text-amber-700 border-amber-200";
    return "bg-slate-100 text-slate-600 border-slate-200";
  };

  const formatLatency = (ms: number | undefined) => {
    if (ms === undefined) return null;
    return ms > 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
  };

  // Helper para renderizar JSON seguro
  const renderJsonBlock = (data: any) => {
    return (
      <pre className="text-[11px] bg-slate-900 text-slate-300 p-3 rounded-xl overflow-x-auto font-mono mt-1 border border-slate-700 custom-scrollbar">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-indigo-100 selection:text-indigo-900 flex flex-col">
      {/* Navbar - Employee Role */}
      <header className="sticky top-0 z-40 border-b border-black/5 bg-slate-800 text-white">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 -ml-2 rounded-lg hover:bg-slate-800 transition-colors text-slate-300 hover:text-white">
              <ChevronLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-indigo-500 flex items-center justify-center shadow-md">
                <Shield strokeWidth={1.5} className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="font-semibold text-sm leading-tight text-white">Auditor Dashboard</h1>
                <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">Hybrid Shield Admin</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
              <span className="text-xs font-bold text-slate-300">AD</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <main className="flex-1 flex overflow-hidden">

        {/* Left Panel: List & Tabs */}
        <div className={`w-full ${selectedJob ? 'hidden lg:flex lg:w-1/3' : 'flex'} flex-col border-r border-slate-200 bg-white`}>
          {/* Tabs */}
          <div className="p-4 border-b border-slate-100 flex gap-2">
            <button
              onClick={() => { setActiveTab("PENDING"); setSelectedJob(null); setExpandedNodeIndex(null); setTraceData(null); }}
              className={`flex-1 py-2.5 px-4 rounded-xl text-sm font-semibold transition-all ${activeTab === "PENDING" ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50'
                }`}
            >
              Pendientes
              {pendingJobs.length > 0 && (
                <span className={`ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs ${activeTab === 'PENDING' ? 'bg-indigo-200 text-indigo-800' : 'bg-slate-200 text-slate-600'}`}>
                  {pendingJobs.length}
                </span>
              )}
            </button>
            <button
              onClick={() => { setActiveTab("HISTORY"); setSelectedJob(null); setExpandedNodeIndex(null); setTraceData(null); }}
              className={`flex-1 py-2.5 px-4 rounded-xl text-sm font-semibold transition-all ${activeTab === "HISTORY" ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50'
                }`}
            >
              Historial
            </button>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            {(activeTab === "PENDING"
              ? pendingJobs.filter(job => {
                const s = (job.status || "").toUpperCase();
                const action = (job.final_action || "").toUpperCase();
                return s === "PENDING_HUMAN_REVIEW" || s === "MANUAL_REVIEW" || s === "PENDING" || (s === "" && action === "HUMAN REVIEW");
              })
              : historicalJobs.filter(job => {
                const s = (job.status || "").toUpperCase();
                const action = (job.final_action || "").toUpperCase();
                return s === "APPROVE" || s === "APPROVED" || s === "BLOCK" || s === "BLOCKED" || s === "FAILED" || s === "ERROR" || action === "APPROVE" || action === "BLOCK";
              }).slice(0, historyLimit)
            ).map((job) => (
              <div
                key={job.thread_id || job.id}
                onClick={() => handleSelectJob(job)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer ${selectedJob?.thread_id === job.thread_id
                    ? 'border-indigo-300 bg-indigo-50/50 shadow-sm'
                    : 'border-slate-100 bg-white hover:border-slate-300 hover:shadow-sm'
                  }`}
              >
                <div className="flex justify-between items-start mb-2">
                  {getStatusBadge(job.final_action)}
                  <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {formatDate(job.last_update || job.created_at || job.timestamp || new Date().toISOString())}
                  </span>
                </div>
                <h3 className="font-semibold text-slate-900 text-sm line-clamp-1">{getJobField(job, 'title') || getJobField(job, 'product_title') || "Producto sin título"}</h3>
                <p className="text-slate-500 text-xs mt-1 line-clamp-2 leading-relaxed">{getJobField(job, 'description') || getJobField(job, 'product_description') || ""}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">${getJobField(job, 'price') || '0.00'}</span>
                  {getJobField(job, 'risk_score') !== undefined && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${getJobField(job, 'risk_score') > 0.8 ? 'bg-rose-100 text-rose-700' :
                        getJobField(job, 'risk_score') > 0.4 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
                      }`}>
                      Risk: {(getJobField(job, 'risk_score') * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            ))}

            {activeTab === "HISTORY" && historicalJobs.length > historyLimit && (
              <button
                onClick={() => setHistoryLimit(prev => prev + 20)}
                className="w-full py-3 mt-4 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-sm font-semibold transition-colors flex items-center justify-center gap-2"
              >
                Cargar 20 más <ChevronDown className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Right Panel: Detail View (Traceability) */}
        {selectedJob && (
          <div className="flex-1 flex flex-col bg-slate-50/50 relative flex">
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="max-w-4xl mx-auto p-6 lg:p-10 space-y-8">

                {/* Mobile Back Button */}
                <button
                  onClick={() => { setSelectedJob(null); setExpandedNodeIndex(null); setTraceData(null); }}
                  className="lg:hidden flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-800 mb-4"
                >
                  <ChevronLeft className="w-4 h-4" /> Volver a la lista
                </button>

                {/* Header Profile */}
                <div className="flex flex-col md:flex-row gap-6 items-start bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
                  <div className="w-full md:w-48 aspect-square rounded-2xl overflow-hidden bg-slate-100 border border-slate-100 shrink-0">
                    <img src={getImageUrl(selectedJob)} alt={getJobField(selectedJob, 'title') || getJobField(selectedJob, 'product_title') || "Producto"} className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1 space-y-4 w-full">
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        {getStatusBadge(selectedJob.final_action)}
                        <span className="text-xs font-medium text-slate-400">ID: {selectedJob.thread_id || selectedJob.id}</span>
                      </div>
                      <h2 className="text-2xl font-bold text-slate-900">{getJobField(selectedJob, 'title') || getJobField(selectedJob, 'product_title') || "Producto"}</h2>
                      <p className="text-sm text-slate-500 mt-2 leading-relaxed">{getJobField(selectedJob, 'description') || getJobField(selectedJob, 'product_description')}</p>
                    </div>
                  </div>
                </div>

                {/* Expanded Metrics Section */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                  <div className="px-4 py-3 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Precio</span>
                    <span className="font-semibold text-slate-700">${getJobField(selectedJob, 'price') || '0.00'} USD</span>
                  </div>
                  <div className="px-4 py-3 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Risk Score</span>
                    <span className={`font-semibold ${getJobField(selectedJob, 'risk_score') > 0.8 ? 'text-rose-600' :
                        getJobField(selectedJob, 'risk_score') > 0.4 ? 'text-amber-600' : 'text-emerald-600'
                      }`}>
                      {((getJobField(selectedJob, 'risk_score') || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="px-4 py-3 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Incertidumbre</span>
                    <span className="font-semibold text-slate-700">{((getJobField(selectedJob, 'uncertainty') || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="px-4 py-3 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Rango Mercado</span>
                    <span className="font-semibold text-slate-700 truncate block" title={getJobField(selectedJob, 'min_price') && getJobField(selectedJob, 'max_price') ? `$${getJobField(selectedJob, 'min_price')} - $${getJobField(selectedJob, 'max_price')}` : "No disponible"}>
                      {getJobField(selectedJob, 'min_price') && getJobField(selectedJob, 'max_price') ? `$${getJobField(selectedJob, 'min_price')} - $${getJobField(selectedJob, 'max_price')}` : "N/A"}
                    </span>
                  </div>
                  <div className="px-4 py-3 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <span className="block text-[10px] font-bold text-slate-400 uppercase mb-1">Ruteo</span>
                    <span className="font-semibold text-slate-700 capitalize truncate block" title={getJobField(selectedJob, 'routing_reason') || "N/A"}>
                      {(getJobField(selectedJob, 'routing_reason') || "N/A").replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>

                {/* Active Signals */}
                {getJobField(selectedJob, 'signals') && Object.entries(getJobField(selectedJob, 'signals')).filter(([_, isActive]) => isActive).length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wide">
                      Señales Activas
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(getJobField(selectedJob, 'signals') as Record<string, boolean>)
                        .filter(([_, isActive]) => isActive)
                        .map(([signalKey]) => (
                          <span key={signalKey} className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${getSignalColor(signalKey)}`}>
                            {signalKey}
                          </span>
                        ))}
                    </div>
                  </div>
                )}

                {/* Policy Violations */}
                {getJobField(selectedJob, 'policy_violations') && getJobField(selectedJob, 'policy_violations').length > 0 && (
                  <div className="bg-rose-50 border border-rose-100 rounded-3xl p-6">
                    <h3 className="text-sm font-bold text-rose-900 flex items-center gap-2 uppercase tracking-wide mb-4">
                      <AlertTriangle className="w-4 h-4 text-rose-600" /> Políticas Infringidas
                    </h3>
                    <div className="space-y-3">
                      {getJobField(selectedJob, 'policy_violations').map((violation: any, i: number) => (
                        <div key={i} className="flex flex-col sm:flex-row gap-3 bg-white/60 p-3 rounded-xl border border-rose-200/50">
                          <span className="font-mono text-xs font-bold text-rose-700 bg-rose-100/50 px-2 py-1 rounded shrink-0 self-start">
                            {violation.policy_id}
                          </span>
                          <span className="text-sm text-rose-800 font-medium">
                            {violation.explanation}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Model Reasoning */}
                {getJobField(selectedJob, 'reasoning') && (
                  <div className="bg-slate-100/80 border border-slate-200 rounded-3xl p-6">
                    <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wide mb-3">
                      Razonamiento del Modelo
                    </h3>
                    <p className="text-sm text-slate-600 leading-relaxed font-medium">
                      {getJobField(selectedJob, 'reasoning')}
                    </p>
                  </div>
                )}

                {/* Pending Actions (if HUMAN REVIEW) */}
                {selectedJob.final_action === "Human Review" && (
                  <div className="bg-white p-6 rounded-3xl border border-indigo-100 shadow-[0_0_40px_rgba(99,102,241,0.05)] space-y-4">
                    <h3 className="font-bold text-slate-900 flex items-center gap-2">
                      <ShieldAlert className="w-5 h-5 text-indigo-500" /> Resolución Requerida
                    </h3>
                    <textarea
                      placeholder="Escribe la justificación de tu decisión..."
                      className="w-full p-4 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 transition-colors resize-none"
                      rows={2}
                      value={justification}
                      onChange={(e) => setJustification(e.target.value)}
                    />
                    <div className="flex gap-3">
                      <button onClick={() => handleDecision('Approve')} className="flex-1 py-3 px-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-colors">
                        <Check className="w-4 h-4" /> Aprobar Publicación
                      </button>
                      <button onClick={() => handleDecision('Block')} className="flex-1 py-3 px-4 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-colors">
                        <X className="w-4 h-4" /> Bloquear Producto
                      </button>
                    </div>
                  </div>
                )}

                {/* Full Traceability (Audit Log) - Expandible Timeline */}
                <div className="bg-white p-6 lg:p-8 rounded-3xl border border-slate-200 shadow-sm">
                  <h3 className="font-bold text-slate-900 mb-8 flex items-center gap-2">
                    <ListTree className="w-5 h-5 text-indigo-500" />
                    Trazabilidad de Nodos (LangGraph Trace)
                  </h3>

                  {isLoadingTrace ? (
                    <div className="flex justify-center items-center py-10">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    </div>
                  ) : (!traceData || !traceData.trace || traceData.trace.length === 0) ? (
                    <p className="text-sm text-slate-500 italic">No hay registros de auditoría forense para este caso.</p>
                  ) : (
                    <div className="flex flex-col space-y-3">
                      {traceData.trace.map((checkpoint: any, i: number) => {
                        const isExpanded = expandedNodeIndex === i;
                        const state = checkpoint.state || {};
                        const hasState = Object.keys(state).length > 0;

                        return (
                          <div
                            key={checkpoint.checkpoint_id || i}
                            className={`rounded-2xl border transition-all duration-300 ${isExpanded ? 'border-indigo-300 bg-indigo-50/20 shadow-md' : 'border-slate-200 bg-slate-50 hover:border-indigo-200 hover:bg-slate-100 hover:shadow-sm cursor-pointer'
                              }`}
                            onClick={() => {
                              if (!isExpanded) setExpandedNodeIndex(i);
                            }}
                          >
                            {/* Collapsed Header */}
                            <div className="flex items-center justify-between p-4">
                              <div className="flex items-center gap-3">
                                <span className="text-xs font-bold text-slate-800 tracking-widest">{checkpoint.next_node || "START"}</span>
                                {getNodeStatusBadge(checkpoint.status || 'completed')}
                              </div>

                              {/* Show X only when expanded */}
                              {isExpanded ? (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedNodeIndex(null);
                                  }}
                                  className="p-1.5 rounded-full hover:bg-slate-200 transition-colors text-slate-500 hover:text-slate-800"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              ) : (
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                              )}
                            </div>

                            {/* Expanded Content */}
                            <AnimatePresence>
                              {isExpanded && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.2, ease: "easeInOut" }}
                                  className="overflow-hidden"
                                >
                                  <div className="px-4 pb-4 cursor-default" onClick={(e) => e.stopPropagation()}>
                                    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                                      <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-3">
                                        <p className="text-sm text-slate-700 leading-relaxed font-medium">
                                          {checkpoint.state?.resumen || "Punto de control de LangGraph"}
                                        </p>
                                        <div className="flex flex-col items-end gap-1 shrink-0 ml-4">
                                          <div className="text-[10px] font-medium text-slate-500 flex items-center gap-1">
                                            <Clock className="w-3 h-3" /> {formatDate(checkpoint.timestamp || new Date().toISOString()).split(',')[1]}
                                          </div>
                                        </div>
                                      </div>

                                      <div className="space-y-4">
                                        {!hasState ? (
                                          <p className="text-xs text-slate-400 italic text-center py-2">Sin estado guardado.</p>
                                        ) : (
                                          <>
                                            {/* State Section */}
                                            {hasState && (
                                              <div>
                                                <h4 className="text-[10px] uppercase tracking-wider font-bold text-indigo-500 mb-2">Estado (Channel Values)</h4>
                                                <div className="space-y-1.5">
                                                  {Object.entries(state)
                                                    .filter(([key]) => key !== "resumen")
                                                    .map(([key, val]) => (
                                                      <div key={key} className="flex flex-col bg-slate-50 border border-slate-100 rounded-lg p-2.5">
                                                        <span className="text-[10px] font-mono font-bold text-slate-500 mb-1">{key}</span>
                                                        {typeof val === 'object' && val !== null ? (
                                                          renderJsonBlock(val)
                                                        ) : (
                                                          <span className="text-xs font-semibold text-slate-800 break-words">{String(val)}</span>
                                                        )}
                                                      </div>
                                                    ))}
                                                </div>
                                              </div>
                                            )}
                                          </>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

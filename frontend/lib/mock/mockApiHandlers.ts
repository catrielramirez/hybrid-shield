import { MOCK_JOBS, mockJobToAnalysisResult } from './mockData';
import type { AnalysisResult, AnalyzeParams } from '@/app/actions/analyze';

// Counter to rotate through different result types
let mockAnalyzeCounter = 0;

// Store mock job states for polling simulation
const mockJobStates = new Map<string, {
  status: string;
  result?: AnalysisResult;
  currentStep: number;
}>();

/**
 * Mock upload - returns a fake job_id instantly
 */
export function mockUpload(params: any): Promise<{ job_id: string }> {
  console.log('[MOCK] Upload called with:', params);
  return Promise.resolve({
    job_id: `mock-job-${Date.now()}`
  });
}

/**
 * Mock analyze - simulates agent processing with progressive states
 * This function initializes a mock job and sets up state progression
 */
export async function mockAnalyze(
  params: AnalyzeParams
): Promise<{ result?: AnalysisResult; error?: string }> {
  console.log('[MOCK] Analyze called for thread_id:', params.thread_id);
  
  // 1. Mantenemos la rotación de estados: Human Review → Block → Approve
  const states = ['Human Review', 'Block', 'Approve'] as const;
  const currentState = states[mockAnalyzeCounter % 3];
  mockAnalyzeCounter++;

  console.log('[MOCK] Returning state:', currentState, `(call #${mockAnalyzeCounter})`);

  let selectedJob;

  // 2. Si el estado actual es 'Block', forzamos el ejemplo del cigarrillo electrónico
  if (currentState === 'Block') {
    selectedJob = MOCK_JOBS.find(j => j.id === "job-block-006");
    if (!selectedJob) {
      console.warn('[MOCK] No se encontró el job-block-006 para el bloqueo. Usando fallback.');
    }
  }

  // 3. Si es 'Approve', 'Human Review' o si falló el paso anterior, buscamos en los otros mocks
  if (!selectedJob) {
    const jobsForState = MOCK_JOBS.filter(j => j.final_action === currentState);
    
    if (jobsForState.length === 0) {
      console.warn('[MOCK] No jobs found for state:', currentState);
      selectedJob = MOCK_JOBS[Math.floor(Math.random() * MOCK_JOBS.length)];
    } else {
      // Elige uno al azar de los que correspondan a ese estado (Aprobado o HITL)
      selectedJob = jobsForState[Math.floor(Math.random() * jobsForState.length)];
    }
  }

  const finalResult = mockJobToAnalysisResult(selectedJob);
  console.log('[MOCK] Selected job:', selectedJob.id, '-', selectedJob.final_action);

  // Initialize the job state for polling
  mockJobStates.set(params.thread_id, {
    status: 'starting',
    result: finalResult,
    currentStep: 0
  });

  // Don't return result immediately - let polling handle it
  return { result: undefined };
}

/**
 * Mock get job status - simulates polling with progressive state updates
 * Returns intermediate states before final result
 */
export async function mockGetJobStatus(jobId: string): Promise<{ 
  status: string; 
  result?: AnalysisResult;
  current_step?: string;
}> {
  console.log('[MOCK] Get job status called for:', jobId);
  
  const jobState = mockJobStates.get(jobId);
  
  if (!jobState) {
    console.error('[MOCK] Job state not found:', jobId);
    return { status: 'error' };
  }

  // Define the processing steps with realistic, variable timing (2-3.5 seconds each)
  const steps = [
    { status: 'starting', label: 'Iniciando análisis de riesgo...', duration: 2000 + Math.random() * 800 },
    { status: 'extracting', label: 'Extrayendo características visuales...', duration: 2200 + Math.random() * 1300 },
    { status: 'rag', label: 'Consultando base de conocimientos (RAG)...', duration: 2500 + Math.random() * 1000 },
    { status: 'evaluating', label: 'Evaluando políticas de e-commerce...', duration: 2300 + Math.random() * 1200 },
    { status: 'done', label: 'Análisis completado', duration: 0 }
  ];

  const currentStep = jobState.currentStep;
  
  // If we've completed all steps, return the final result
  if (currentStep >= steps.length - 1) {
    console.log('[MOCK] Job completed:', jobId);
    mockJobStates.delete(jobId); // Clean up
    return {
      status: 'done',
      result: jobState.result
    };
  }

  // Progress to the next step
  jobState.currentStep += 1;
  const nextStep = steps[jobState.currentStep];
  jobState.status = nextStep.status;
  
  console.log('[MOCK] Job progressing to:', nextStep.status);

  return {
    status: nextStep.status,
    current_step: nextStep.label
  };
}

/**
 * Mock get trace - returns the trace for a given job_id
 */
export async function mockGetTrace(jobId: string): Promise<any> {
  console.log('[MOCK] Get trace called for job:', jobId);
  
  // Simulate network delay (1-2 seconds)
  const delay = 1000 + Math.random() * 1000;
  await new Promise(resolve => setTimeout(resolve, delay));

  const job = MOCK_JOBS.find(j => j.id === jobId || j.thread_id === jobId);
  
  if (!job) {
    console.error('[MOCK] Job not found:', jobId);
    throw new Error(`Job ${jobId} not found in mock data`);
  }

  console.log('[MOCK] Returning trace with', job.trace.length, 'checkpoints');

  return {
    trace: job.trace,
    job_id: jobId,
    status: 'completed'
  };
}

/**
 * Mock submit decision - logs and returns success
 */
export async function mockSubmitDecision(
  jobId: string,
  decision: 'Approve' | 'Block'
): Promise<{ ok: boolean }> {
  console.log('[MOCK] Decision submitted for', jobId, ':', decision);
  
  // Simulate API delay (500ms)
  await new Promise(resolve => setTimeout(resolve, 500));

  return { ok: true };
}

/**
 * Mock get image URL - returns the image_url from the job
 */
export function mockGetImageUrl(jobId: string): string {
  const job = MOCK_JOBS.find(j => j.id === jobId || j.thread_id === jobId);
  const url = job?.image_url || '/placeholder.png';
  console.log('[MOCK] Image URL for', jobId, ':', url);
  return url;
}

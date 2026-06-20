"use server";

import { mockAnalyze, mockGetJobStatus } from '@/lib/mock/mockApiHandlers';

export type AnalysisStatus =
  | "idle"
  | "starting"
  | "extracting"
  | "rag"
  | "evaluating"
  | "done"
  | "error";

export interface PolicyCitation {
  policy_id: string;
  policy_title: string;
  snippet: string;
  reason: string;
  relevance_score: number;
}

export interface RiskFactor {
  factor: string;
  weight: number;
}

export interface PolicyViolation {
  policy_id: string;
  factor: string;
  explanation: string;
}

export interface AnalysisResult {
  risk_score: number;
  final_action: "Approve" | "Human Review" | "Block";
  reasoning: string;
  features: {
    primary_object?: string;
    object_category?: string;
    objects_detected?: string[];
    text_in_image?: string[];
    contact_info_detected?: boolean;
    visual_dissonance?: boolean;
    product_condition?: string;
    condition_issue_detected?: boolean;
    image_quality?: string;
    image_type?: string;
    is_sellable?: boolean;
    fraud_signals?: string[];
    confidence?: number;
    error?: string;
  };
  signals: {
    visual_dissonance: boolean;
    contact_info_detected: boolean;
    price_anomaly: boolean;
    condition_issue?: boolean;
    policy_match: boolean;
  };
  policy_citations?: PolicyCitation[];
  risk_breakdown?: RiskFactor[];
  policy_violations?: PolicyViolation[];
  pipeline_steps?: string[];
  uncertainty?: number;
  status?: string;
  error?: string;
}

export interface AnalyzeParams {
  thread_id: string;
  gcs_uri: string;
  title: string;
  description: string;
  price: number;
}

/**
 * Wait for Analysis (Polling)
 * This function now polls the backend until the event-driven agent 
 * finishes processing and writes the results to Firestore.
 */
export async function analyzeProduct(
  params: AnalyzeParams
): Promise<{ result?: AnalysisResult; error?: string }> {
  try {
    // Use mock handler in mock mode
    if (process.env.NEXT_PUBLIC_DATA_SOURCE === 'mock') {
      // Initialize the mock job
      await mockAnalyze(params);
      
      // Simulate polling with state progression
      const maxAttempts = 6; // 6 attempts for all states
      let attempts = 0;
      const delay = 1200; // 1.2s between polls

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, delay));
        
        const statusResponse = await mockGetJobStatus(params.thread_id);
        
        if (statusResponse.status === 'done' && statusResponse.result) {
          console.log('[MOCK] Analysis complete');
          return { result: statusResponse.result };
        }
        
        if (statusResponse.status === 'error') {
          return { error: 'Mock analysis failed' };
        }
        
        console.log('[MOCK] Current status:', statusResponse.status);
        attempts++;
      }
      
      return { error: 'Mock analysis timeout' };
    }

    const { thread_id } = params;

    if (!thread_id) {
      return { error: "Missing thread_id for tracking." };
    }

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    
    let attempts = 0;
    const maxAttempts = 3; // 3 * 5s = 15s timeout
    const delay = 5000;

    console.log(`Starting polling for job_id: ${thread_id}`);

    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`${backendUrl}/api/jobs/${thread_id}`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
          cache: 'no-store'
        });

        if (response.ok) {
          const jobData = await response.json();
          
          // Check if analysis is complete
          // The agent sets status to "done" or provides a "final_action"
          if (jobData.status === "done" || jobData.final_action) {
            console.log(`Analysis complete for ${thread_id}`);
            return { result: jobData as AnalysisResult };
          }

          if (jobData.status === "error" || jobData.status === "FAILED") {
            return { error: jobData.error || "El agente de moderación experimentó un error crítico. Intente más tarde." };
          }
          
          console.log(`Job ${thread_id} status: ${jobData.status || "PENDING"} (attempt ${attempts + 1})`);
        } else {
          // If the server returns a non-OK status (like 500 or 400), we handle it
          try {
            const errData = await response.json();
            const detail = errData.detail || "Error en el procesamiento del job.";
            console.error(`Polling received server error status ${response.status}: ${detail}`);
            return { error: `Error del servidor: ${detail}. Por favor, intente más tarde.` };
          } catch {
            console.error(`Polling received empty or invalid error response, status ${response.status}`);
            // If it's a 404, allow some retries because Firestore might be slightly delayed in registering the doc
            if (response.status !== 404 || attempts > 5) {
              return { error: "El backend reportó un error y no se pudo completar el análisis. Intente más tarde." };
            }
          }
        }
      } catch (fetchErr: any) {
        console.error("Fetch network error during polling:", fetchErr);
        return { error: "No se pudo establecer conexión con el servidor. Verifique si el servicio de backend está activo e intente más tarde." };
      }

      attempts++;
      await new Promise(resolve => setTimeout(resolve, delay));
    }

    return { error: "El análisis está tardando más de lo esperado. Por favor, intente más tarde." };

  } catch (err: unknown) {
    console.error("Polling Action Error:", err);
    const message =
      err instanceof Error
        ? err.message
        : "An unexpected error occurred during polling";
    return { error: message };
  }
}

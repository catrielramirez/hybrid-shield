"use server";

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
  status?: string;
  final_action?: "Approve" | "Human Review" | "Block";
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
    const { thread_id } = params;

    if (!thread_id) {
      return { error: "Missing thread_id for tracking." };
    }

    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
    
    let attempts = 0;
    const maxAttempts = 60; // 60 * 2s = 120s timeout
    const delay = 2000;

    console.log(`Starting polling for job_id: ${thread_id}`);

    while (attempts < maxAttempts) {
      const response = await fetch(`${baseUrl}/api/jobs/${thread_id}`, {
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

        if (jobData.status === "error") {
          return { error: jobData.error || "Moderation agent encountered an error." };
        }
        
        console.log(`Job ${thread_id} status: ${jobData.status || "PENDING"} (attempt ${attempts + 1})`);
      }

      attempts++;
      await new Promise(resolve => setTimeout(resolve, delay));
    }

    return { error: "El análisis está tardando más de lo esperado. Por favor, revisa más tarde." };

  } catch (err: unknown) {
    console.error("Polling Action Error:", err);
    const message =
      err instanceof Error
        ? err.message
        : "An unexpected error occurred during polling";
    return { error: message };
  }
}

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
  policy_signals?: {
    banned_object?: boolean;
    product_unusable?: boolean;
    low_quality_image?: boolean;
    external_contact?: boolean;
  };
  model_metadata?: {
    vision_model: string;
    reasoning_model: string;
    rag_index: string;
  };
  pipeline_steps?: {
    node: string;
    status: "completed" | "skipped";
    summary?: string;
  }[];
  uncertainty: number;
  risk_breakdown: RiskFactor[];
  rag_context?: string;
  policy_citations?: PolicyCitation[];
  policy_violations?: PolicyViolation[];
  status?: string;
}

export interface AnalyzeParams {
  thread_id: string;
  gcs_uri: string;
  title: string;
  description: string;
  price: number;
}

export async function analyzeProduct(
  params: AnalyzeParams
): Promise<{ result?: AnalysisResult; error?: string }> {
  try {
    const { thread_id, gcs_uri, title, description, price } = params;

    if (!title || !description || !gcs_uri || !thread_id) {
      return { error: "Missing required product metadata or image URI." };
    }

    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

    // Call the proxy Gateway → Python backend
    const response = await fetch(`${baseUrl}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id,
        gcs_uri,
        title,
        description,
        price,
      }),
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error ||
          `Moderation API failed with status ${response.status}`
      );
    }

    const result = (await response.json()) as AnalysisResult;
    return { result };
  } catch (err: unknown) {
    console.error("Analysis Action Error:", err);
    const message =
      err instanceof Error
        ? err.message
        : "An unexpected error occurred during analysis";
    return { error: message };
  }
}


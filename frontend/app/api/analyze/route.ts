import { NextResponse } from "next/server";

/**
 * Moderation API Gateway — Pure JSON Proxy
 * Forwards { title, description, price, image_path } to the Python/LangGraph backend.
 */

interface AnalyzePayload {
  thread_id: string;
  gcs_uri: string;
  title: string;
  description: string;
  price: number;
}

export async function POST(req: Request) {
  try {
    const payload: AnalyzePayload = await req.json();

    const BACKEND_URL =
      process.env.MODERATION_SERVICE_URL || "http://localhost:8000/analyze";

    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: payload.thread_id,
        gcs_uri: payload.gcs_uri,
        title: payload.title,
        description: payload.description,
        price: payload.price
      }),
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(
        `Backend failed with status ${response.status}: ${errorBody}`
      );
      return NextResponse.json(
        { error: "Moderation pipeline execution failed", detail: errorBody },
        { status: response.status }
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("API Gateway Error:", error);
    return NextResponse.json(
      { error: "Moderation service is currently unavailable" },
      { status: 500 }
    );
  }
}

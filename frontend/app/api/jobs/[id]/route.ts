import { NextResponse } from "next/server";

/**
 * Proxy for Backend /jobs/{job_id} Endpoint
 * GET /api/jobs/[id]
 */

export async function GET(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = await params;

    if (!id) {
      return NextResponse.json({ error: "Job ID is required" }, { status: 400 });
    }

    const baseUrl = process.env.BACKEND_SERVICE_URL || "http://localhost:8000";
    const targetUrl = `${baseUrl.replace(/\/$/, "")}/jobs/${id}`;
    
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      // Important for polling: prevent caching
      cache: 'no-store'
    });

    if (!response.ok) {
        if (response.status === 404) {
            return NextResponse.json({ error: "Job not found" }, { status: 404 });
        }
        const errorBody = await response.text();
        return NextResponse.json(
          { error: "Failed to fetch job status", detail: errorBody },
          { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("API Gateway Error (get-job-status):", error);
    return NextResponse.json(
      { error: "Moderation service is currently unavailable" },
      { status: 500 }
    );
  }
}

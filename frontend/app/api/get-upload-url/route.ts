import { NextResponse } from "next/server";

/**
 * Proxy for Backend /get-upload-url Endpoint
 * POST /api/get-upload-url
 */

export async function POST(req: Request) {
  try {
    const payload = await req.json();

    if (!payload.filename) {
      return NextResponse.json({ error: "Filename is required" }, { status: 400 });
    }

    const BACKEND_SERVICE_URL =
      process.env.BACKEND_SERVICE_URL || "http://127.0.0.1:8000";
    
    const targetUrl = `${BACKEND_SERVICE_URL}/get-upload-url`;

    const response = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorBody = await response.text();
        return NextResponse.json(
          { error: "Failed to generate upload URL", detail: errorBody },
          { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("API Gateway Error (get-upload-url):", error);
    return NextResponse.json(
      { error: "Moderation service is currently unavailable" },
      { status: 500 }
    );
  }
}

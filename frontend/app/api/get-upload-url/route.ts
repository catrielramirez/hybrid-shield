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

    const baseUrl = process.env.BACKEND_SERVICE_URL || "http://localhost:8000";
    const targetUrl = `${baseUrl.replace(/\/$/, "")}/get-upload-url`;
    
    console.log("Forwarding to:", targetUrl);

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

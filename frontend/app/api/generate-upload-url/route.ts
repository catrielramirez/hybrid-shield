import { NextResponse } from "next/server";

/**
 * Proxy for GCS Signed URL Generation
 * GET /api/generate-upload-url?filename=...
 */

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const filename = searchParams.get("filename");

    if (!filename) {
      return NextResponse.json({ error: "Filename is required" }, { status: 400 });
    }

    const BACKEND_SERVICE_URL =
      process.env.MODERATION_SERVICE_URL?.replace("/analyze", "") || "http://localhost:8000";
    
    const targetUrl = `${BACKEND_SERVICE_URL}/generate-upload-url?filename=${encodeURIComponent(filename)}`;

    const response = await fetch(targetUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
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
    console.error("API Gateway Error (generate-upload-url):", error);
    return NextResponse.json(
      { error: "Moderation service is currently unavailable" },
      { status: 500 }
    );
  }
}

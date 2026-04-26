import { NextResponse } from "next/server";

/**
 * Proxy for Backend Unified Ingestion Endpoint
 * POST /api/metadata
 */

interface MetadataPayload {
  job_id: string;
  filename: string;
  content_type: string;
  title: string;
  description: string;
  price: number;
}

export async function POST(req: Request) {
  try {
    const payload: MetadataPayload = await req.json();

    // 1. Validaciones básicas de entrada
    if (!payload.filename || !payload.title || !payload.description) {
      return NextResponse.json(
        { error: "Missing required fields: filename, title, description" },
        { status: 400 }
      );
    }

    // 2. Configuración de la URL (Prioridad .env.local)
    const BACKEND_SERVICE_URL =
      process.env.BACKEND_SERVICE_URL || "http://127.0.0.1:8000";

    // 3. Petición al Backend en Cloud Run
    const response = await fetch(`${BACKEND_SERVICE_URL}/metadata`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(15000), // Evita esperas infinitas
    });

    // 4. Manejo de respuesta del backend
    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Backend /metadata failed (${response.status}): ${errorBody}`);
      return NextResponse.json(
        { error: "Failed to initialize ingestion", detail: errorBody },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error("API Gateway Error (metadata):", error);
    return NextResponse.json(
      { error: "Moderation service is currently unavailable or connection timed out" },
      { status: 500 }
    );
  }
}
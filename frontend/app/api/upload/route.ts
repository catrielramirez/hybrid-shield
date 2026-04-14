import { NextRequest, NextResponse } from "next/server";
import { Storage } from "@google-cloud/storage";
import { v4 as uuidv4 } from "uuid";

// Initialize GCS client
// Vercel will use GOOGLE_APPLICATION_CREDENTIALS if provided as an environment variable
// or it will use the default credentials if running in a Google Cloud environment.
const storage = new Storage();
const bucketName = process.env.GCS_BUCKET_NAME;

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    if (!bucketName) {
      console.error("GCS_BUCKET_NAME is not defined in environment variables");
      return NextResponse.json({ error: "Server configuration error: Bucket not configured" }, { status: 500 });
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Generate a unique filename using uuid
    const uniqueName = `${uuidv4()}-${file.name.replace(/\s+/g, "-")}`;
    
    // Upload directly to Google Cloud Storage
    const bucket = storage.bucket(bucketName);
    const gcsFile = bucket.file(uniqueName);

    await gcsFile.save(buffer, {
      metadata: {
        contentType: file.type,
      },
      resumable: false,
    });

    // Return the GCS URI
    const url = `gs://${bucketName}/${uniqueName}`;

    return NextResponse.json({ image_url: url });
  } catch (error) {
    // Log errors to console (these will go to Vercel logs)
    console.error("GCS Upload error:", error);
    
    return NextResponse.json(
      { error: `Upload failed: ${(error as Error).message}` }, 
      { status: 500 }
    );
  }
}


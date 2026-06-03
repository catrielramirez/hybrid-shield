import { initializeApp, getApps, getApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// The config will use env variables if available, otherwise it allows a graceful fallback
// Since this is a POC, make sure you add NEXT_PUBLIC_FIREBASE_* env vars later
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "mock-key",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "mock-domain",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "hybrid-shield",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "mock-bucket",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "mock-sender",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "mock-app-id"
};

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

// Connect to the specific database 'firestore-hybrid-shield' as used in the backend
const db = getFirestore(app, "firestore-hybrid-shield");

export { app, db };

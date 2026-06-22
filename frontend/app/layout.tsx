import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hybrid Shield — E-commerce Fraud Detector",
  description: "AI-powered moderation dashboard for e-commerce content fraud detection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}

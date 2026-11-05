import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Agentic Workspace Platform | Cyber-Glass Spatial Canvas",
  description: "Multi-tenant spatial AI-agent orchestration and HITL collaborative canvas",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-void text-zinc-100 antialiased selection:bg-[#8B5CF6]/30 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}


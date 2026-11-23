import React from "react";
import Link from "next/link";
import { Layers, Compass, ArrowLeft, ArrowRight, Sparkles } from "lucide-react";

export default function NotFound() {
  return (
    <div className="relative min-h-screen bg-void flex flex-col items-center justify-center p-4 overflow-hidden text-center">
      {/* Background cyber glow spheres */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#8B5CF6]/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-[#06B6D4]/15 rounded-full blur-[120px] pointer-events-none" />

      {/* Cyber Glass Card */}
      <div className="relative z-10 w-full max-w-lg rounded-2xl border border-white/10 bg-[#0B0F19]/85 p-8 shadow-2xl backdrop-blur-cyber">
        {/* Neon Brand Badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-3.5 py-1 text-xs font-mono text-[#8B5CF6] mb-6">
          <Sparkles className="h-3.5 w-3.5" />
          404: Node Disconnected In The Void
        </div>

        {/* 404 Glitch Number */}
        <div className="text-7xl font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-[#8B5CF6] via-[#06B6D4] to-purple-400 mb-2 font-mono">
          404
        </div>

        <h2 className="text-xl font-bold text-white mb-2">
          Spatial Canvas Route Not Found
        </h2>

        <p className="text-xs text-zinc-400 max-w-sm mx-auto leading-relaxed mb-8">
          The requested agent node, workspace route, or AST canvas checkpoint does not
          exist in this cluster or has been decommissioned.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/workspace/default/canvas"
            className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl bg-[#8B5CF6] px-5 py-2.5 text-xs font-semibold text-white shadow-neon-violet hover:bg-[#7C3AED] transition-all"
          >
            Launch Spatial Canvas
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>

          <Link
            href="/"
            className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-xs font-medium text-zinc-300 hover:border-white/20 hover:text-white transition-all"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Return Home
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-xs text-zinc-600 font-mono">
        AGENTIC.VOID // Cluster: Alpha-US-East
      </div>
    </div>
  );
}


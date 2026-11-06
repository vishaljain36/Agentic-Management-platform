import Link from "next/link";
import { Layers, ArrowRight, Shield, Zap, Sparkles, Cpu } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen bg-void flex flex-col justify-between overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#8B5CF6]/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-[#06B6D4]/15 rounded-full blur-[120px] pointer-events-none" />

      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-6 z-10 border-b border-white/5 backdrop-blur-cyber">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-[#8B5CF6] to-[#06B6D4] shadow-neon-violet">
            <Layers className="h-5 w-5 text-white" />
          </div>
          <span className="text-base font-bold tracking-wider text-white">
            AGENTIC<span className="text-[#8B5CF6]">.VOID</span>
          </span>
        </div>

        <Link
          href="/workspace/default/canvas"
          className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-zinc-200 hover:border-[#8B5CF6]/50 hover:bg-[#8B5CF6]/10 transition-all"
        >
          Open Spatial Canvas
        </Link>
      </nav>

      {/* Hero */}
      <main className="z-10 flex flex-col items-center justify-center text-center px-4 max-w-4xl mx-auto my-auto py-16">
        <div className="inline-flex items-center gap-2 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-3 py-1 text-xs font-mono text-[#8B5CF6] mb-6">
          <Sparkles className="h-3.5 w-3.5" />
          Next.js 15 Cyber-Glass Spatial Swarm Platform
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white max-w-3xl leading-tight">
          Spatial Multi-Agent Orchestration with{" "}
          <span className="bg-gradient-to-r from-[#8B5CF6] via-[#06B6D4] to-[#10B981] bg-clip-text text-transparent">
            Human-In-The-Loop
          </span>{" "}
          Guardrails
        </h1>

        <p className="mt-6 text-base sm:text-lg text-zinc-400 max-w-2xl leading-relaxed">
          Wire cyclical LangGraph agent state machines on an infinite reactive canvas.
          Execute vector-grounded RAG, inspect streaming AST reasoning, and safely authorize Docker code sandboxes.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/workspace/default/canvas"
            className="flex items-center gap-2 rounded-xl bg-[#8B5CF6] px-6 py-3.5 text-sm font-semibold text-white shadow-neon-violet hover:bg-[#7C3AED] transition-all"
          >
            Launch Spatial Canvas
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-6 py-3.5 text-sm font-medium text-zinc-300 hover:border-white/20 hover:text-white transition-all"
          >
            API Swagger Docs
          </a>
        </div>

        {/* Feature Highlights Grid */}
        <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-4 w-full text-left">
          <div className="rounded-xl border border-white/10 bg-[#111827]/60 p-4 backdrop-blur-cyber">
            <Zap className="h-5 w-5 text-[#8B5CF6] mb-2" />
            <h3 className="text-sm font-semibold text-zinc-100">Kinetic Spatial Flows</h3>
            <p className="text-xs text-zinc-400 mt-1">Real-time pulse edge transitions across multi-agent cycles.</p>
          </div>

          <div className="rounded-xl border border-white/10 bg-[#111827]/60 p-4 backdrop-blur-cyber">
            <Shield className="h-5 w-5 text-[#F59E0B] mb-2" />
            <h3 className="text-sm font-semibold text-zinc-100">HITL AST Pre-Screen</h3>
            <p className="text-xs text-zinc-400 mt-1">Interruption gate halts code execution before Docker sandboxing.</p>
          </div>

          <div className="rounded-xl border border-white/10 bg-[#111827]/60 p-4 backdrop-blur-cyber">
            <Cpu className="h-5 w-5 text-[#06B6D4] mb-2" />
            <h3 className="text-sm font-semibold text-zinc-100">Qdrant Vector Isolation</h3>
            <p className="text-xs text-zinc-400 mt-1">Multi-tenant embedded document collections partitioned per workspace.</p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 px-8 py-4 text-center text-xs text-zinc-500 z-10">
        Agentic Management Platform © 2026. Built with Next.js 15, React Flow & FastAPI LangGraph.
      </footer>
    </div>
  );
}


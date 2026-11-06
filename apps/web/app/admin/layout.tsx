import React from "react";
import Link from "next/link";
import { ShieldAlert, BarChart3, Cpu, Users, ChevronRight, Activity } from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#030712] text-zinc-100 flex flex-col font-sans">
      {/* Super Admin Top Header */}
      <header className="h-16 border-b border-white/10 bg-[#0B0F19]/80 backdrop-blur-cyber px-6 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400">
            <ShieldAlert size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-red-400">
                Super Admin Console
              </span>
              <span className="text-[10px] bg-red-500/10 border border-red-500/30 text-red-300 px-1.5 py-0.5 rounded font-mono">
                ROOT PRIVILEGES
              </span>
            </div>
            <p className="text-xs text-zinc-400">AGENTIC.VOID Orchestration Platform</p>
          </div>
        </div>

        {/* Admin Navigation Links */}
        <nav className="flex items-center gap-1">
          <Link
            href="/admin/metrics"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
          >
            <BarChart3 size={14} className="text-[#06B6D4]" />
            Platform Margins
          </Link>
          <Link
            href="/admin/providers"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Cpu size={14} className="text-[#8B5CF6]" />
            LLM Providers
          </Link>
          <Link
            href="/admin/users"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Users size={14} className="text-[#10B981]" />
            User Management
          </Link>
          <div className="h-4 w-px bg-white/10 mx-2" />
          <Link
            href="/workspace/default/canvas"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
          >
            <span>Exit to Canvas</span>
            <ChevronRight size={14} />
          </Link>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}


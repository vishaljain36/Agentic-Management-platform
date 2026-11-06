"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Layers,
  Bot,
  Activity,
  Cpu,
  Coins,
  Search,
  Command,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import { formatTokens, formatUsd } from "@/lib/utils";
import { useAgentStore } from "@/store/use-agent-store";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { totalTokens, costUsd, status } = useAgentStore();
  const [activeWorkspace, setActiveWorkspace] = useState("Enterprise Workspace Alpha");

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-void">
      {/* Top Navigation HUD */}
      <header className="flex h-14 w-full shrink-0 items-center justify-between border-b border-white/10 bg-[#0B0F19]/80 px-4 backdrop-blur-cyber z-20">
        {/* Left: Brand & Workspace Selector */}
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-[#8B5CF6] to-[#06B6D4] shadow-neon-violet">
              <Layers className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-bold tracking-wider text-white">
              AGENTIC<span className="text-[#8B5CF6]">.VOID</span>
            </span>
          </Link>

          <div className="h-4 w-[1px] bg-white/10" />

          {/* Workspace selector dropdown */}
          <button className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-zinc-300 hover:border-white/20 hover:text-white">
            <div className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>{activeWorkspace}</span>
            <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
          </button>
        </div>

        {/* Center: Swarm Status indicator */}
        <div className="hidden md:flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/40 px-3 py-1 text-xs">
            <Bot className="h-3.5 w-3.5 text-[#8B5CF6]" />
            <span className="text-zinc-400">Swarm Engine:</span>
            <span
              className={`font-mono text-[11px] font-semibold ${
                status === "RUNNING"
                  ? "text-[#06B6D4] animate-pulse"
                  : status === "WAITING_FOR_HUMAN"
                  ? "text-[#F59E0B]"
                  : "text-emerald-400"
              }`}
            >
              {status}
            </span>
          </div>
        </div>

        {/* Right: Token HUD, Search, Cmd+K */}
        <div className="flex items-center gap-3">
          {/* Token Meter */}
          <div className="flex items-center gap-2 rounded-lg border border-[#06B6D4]/30 bg-[#06B6D4]/10 px-3 py-1 font-mono text-xs text-[#06B6D4]">
            <Coins className="h-3.5 w-3.5" />
            <span>{formatTokens(totalTokens)} Tok</span>
            <span className="text-zinc-500">|</span>
            <span className="text-emerald-400">{formatUsd(costUsd)}</span>
          </div>

          {/* Command Palette Trigger */}
          <button className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-zinc-400 hover:border-white/20 hover:text-zinc-200">
            <Search className="h-3 w-3" />
            <span className="hidden sm:inline">Search Swarm</span>
            <kbd className="rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400 border border-white/10">
              Cmd + K
            </kbd>
          </button>
        </div>
      </header>

      {/* Main Spatial Body */}
      <div className="flex-1 overflow-hidden relative">{children}</div>
    </div>
  );
}


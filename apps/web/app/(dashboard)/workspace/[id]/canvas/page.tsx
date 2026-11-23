"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import {
  Loader2,
  Plus,
  Bot,
  Sparkles,
  Terminal,
  Activity,
  Layers,
  Compass,
  Sliders,
  Box,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamChat } from "@/components/chat/stream-chat";
import { ThoughtTree } from "@/components/chat/thought-tree";
import { HitlModal } from "@/components/canvas/hitl-modal";
import { SandboxTerminal } from "@/components/sandbox/terminal";
import { AgentBuilderDrawer } from "@/components/agents/agent-builder-drawer";
import { UsageGauge } from "@/components/dashboard/usage-gauge";
import { useAgentStore } from "@/store/use-agent-store";
import { useWorkspaceStore } from "@/store/use-workspace-store";
import { SpatialCanvas } from "@/components/canvas/SpatialCanvas";

// SSR-Safe Dynamic Import of 3D WebGL Spatial Canvas
const SpatialCanvas3D = dynamic(
  () => import("@/components/canvas3d/SpatialCanvas3D"),
  {
    ssr: false,
    loading: () => (
      <div className="fixed inset-0 z-0 flex flex-col items-center justify-center bg-[#030712] text-zinc-400">
        <Loader2 className="h-8 w-8 animate-spin text-[#8B5CF6] mb-3" />
        <span className="font-mono text-xs tracking-wider uppercase text-zinc-300">
          Initializing 3D WebGL Spatial Canvas...
        </span>
      </div>
    ),
  }
);

export default function WorkspaceCanvasPage() {
  const [viewMode, setViewMode] = useState<"3D" | "2D">("3D");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const { activeNode, status, totalTokens } = useAgentStore();
  const {
    activeAgentId,
    sandboxingAgentId,
    hitlPausedAgentId,
  } = useWorkspaceStore();

  return (
    <div className="relative h-full w-full overflow-hidden bg-void select-none">
      {/* ================================================================== */}
      {/* LAYER 0: 3D WebGL Canvas (or 2D React Flow Fallback)               */}
      {/* ================================================================== */}
      {viewMode === "3D" ? (
        <SpatialCanvas3D />
      ) : (
        <div className="fixed inset-0 z-0 h-full w-full">
          <SpatialCanvas />
        </div>
      )}

      {/* ================================================================== */}
      {/* LAYER 1: Floating 2D HUD Layout (pointer-events-none container)     */}
      {/* ================================================================== */}
      <div className="relative z-10 flex h-full w-full flex-col justify-between pointer-events-none p-4">
        {/* --- Top HUD Row --- */}
        <div className="flex items-start justify-between w-full">
          {/* View Mode & Swarm Controls Toggle */}
          <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-white/10 bg-[#0B0F19]/85 p-1.5 backdrop-blur-cyber shadow-2xl">
            <button
              onClick={() => setViewMode("3D")}
              data-testid="toggle-view-3d"
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                viewMode === "3D"
                  ? "bg-[#8B5CF6] text-white shadow-neon-violet"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Box className="h-3.5 w-3.5" />
              <span>3D WebGL Canvas</span>
            </button>

            <button
              onClick={() => setViewMode("2D")}
              data-testid="toggle-view-2d"
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                viewMode === "2D"
                  ? "bg-[#06B6D4] text-white shadow-neon-cyan"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>2D Flow Mode</span>
            </button>

            <div className="h-4 w-[1px] bg-white/10 mx-1" />

            <button
              onClick={() => setIsDrawerOpen(true)}
              data-testid="open-builder-drawer-btn"
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs font-medium text-zinc-200 hover:border-[#8B5CF6]/50 hover:bg-[#8B5CF6]/10 transition-all"
            >
              <Plus className="h-3.5 w-3.5 text-[#8B5CF6]" />
              <span>Agent Builder</span>
            </button>
          </div>

          {/* Floating Metered Usage Gauge */}
          <div className="pointer-events-auto w-64 shadow-2xl backdrop-blur-cyber">
            <UsageGauge
              usedCredits={totalTokens > 0 ? totalTokens : 24800}
              totalCredits={100000}
            />
          </div>
        </div>

        {/* --- Middle Floating Sidebars --- */}
        <div className="flex flex-1 items-center justify-between py-2 overflow-hidden">
          {/* Left Panel: Swarm Nodes List */}
          <aside className="pointer-events-auto flex max-h-[460px] w-64 flex-col rounded-2xl border border-white/10 bg-[#0B0F19]/85 p-3.5 backdrop-blur-cyber shadow-2xl">
            <div className="mb-2.5 flex items-center justify-between border-b border-white/5 pb-2">
              <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-300">
                <Bot className="h-4 w-4 text-[#8B5CF6]" />
                Swarm Graph Nodes
              </span>
              <span className="rounded bg-[#8B5CF6]/20 px-1.5 py-0.5 text-[9px] font-mono text-[#8B5CF6]">
                {viewMode}
              </span>
            </div>

            <div className="flex-1 space-y-2 overflow-y-auto pr-1">
              {/* Researcher */}
              <div
                className={`rounded-lg border p-2.5 transition-all ${
                  activeAgentId === "researcher"
                    ? "border-[#06B6D4] bg-[#06B6D4]/10 shadow-[0_0_12px_rgba(6,182,212,0.3)]"
                    : "border-white/5 bg-black/40 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
                  <span>Researcher Agent</span>
                  <span
                    className={`rounded px-1 text-[9px] ${
                      activeAgentId === "researcher"
                        ? "bg-[#06B6D4]/30 text-[#06B6D4]"
                        : "bg-white/5 text-zinc-400"
                    }`}
                  >
                    {activeAgentId === "researcher" ? "Active" : "Ready"}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-zinc-400">
                  Vector Retrieval & Web Context
                </p>
              </div>

              {/* Evaluator */}
              <div
                className={`rounded-lg border p-2.5 transition-all ${
                  sandboxingAgentId === "evaluator"
                    ? "border-[#F59E0B] bg-[#F59E0B]/10 shadow-[0_0_12px_rgba(245,158,11,0.3)]"
                    : "border-white/5 bg-black/40 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
                  <span>Evaluator Agent</span>
                  <span
                    className={`rounded px-1 text-[9px] ${
                      sandboxingAgentId === "evaluator"
                        ? "bg-[#F59E0B]/30 text-[#F59E0B]"
                        : "bg-white/5 text-zinc-400"
                    }`}
                  >
                    {sandboxingAgentId === "evaluator" ? "Sandbox" : "Ready"}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-zinc-400">
                  AST Mutation & Code Validation
                </p>
              </div>

              {/* HITL */}
              <div
                className={`rounded-lg border p-2.5 transition-all ${
                  hitlPausedAgentId
                    ? "border-[#EF4444] bg-[#EF4444]/10 shadow-[0_0_12px_rgba(239,68,68,0.35)]"
                    : "border-white/5 bg-black/40 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
                  <span>HITL Checkpoint</span>
                  <span
                    className={`rounded px-1 text-[9px] ${
                      hitlPausedAgentId
                        ? "bg-red-500/30 text-red-400 animate-pulse"
                        : "bg-white/5 text-zinc-400"
                    }`}
                  >
                    {hitlPausedAgentId ? "Paused" : "Review"}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-zinc-400">
                  Administrator Consent Gate
                </p>
              </div>

              {/* Writer */}
              <div className="rounded-lg border border-white/5 bg-black/40 p-2.5 hover:border-white/20 transition-all">
                <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
                  <span>Final Writer</span>
                  <span className="rounded bg-white/5 px-1 text-[9px] text-zinc-400">
                    Sink
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-zinc-400">
                  Synthesis & Report Markdown
                </p>
              </div>
            </div>

            {/* Quick Add Custom Agent */}
            <div className="mt-3 border-t border-white/5 pt-3">
              <Button
                size="sm"
                variant="secondary"
                className="w-full flex items-center justify-center gap-1.5 text-xs bg-white/5 hover:bg-[#8B5CF6]/20 border border-white/10"
                onClick={() => setIsDrawerOpen(true)}
              >
                <Plus className="h-3.5 w-3.5 text-[#8B5CF6]" />
                Configure New Agent
              </Button>
            </div>
          </aside>

          {/* Right Panel: Sandbox Terminal */}
          <aside className="pointer-events-auto flex max-h-[460px] w-80 flex-col rounded-2xl border border-white/10 bg-[#0B0F19]/85 p-3.5 backdrop-blur-cyber shadow-2xl">
            <SandboxTerminal />
          </aside>
        </div>

        {/* --- Bottom Floating Telemetry Panel (Stream Chat + Thought Tree) --- */}
        <div className="pointer-events-auto mx-auto w-[92%] max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-3 h-52">
          <StreamChat />
          <ThoughtTree />
        </div>
      </div>

      {/* ================================================================== */}
      {/* LAYER 2: Modals & Drawers                                          */}
      {/* ================================================================== */}
      <HitlModal />
      <AgentBuilderDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
}

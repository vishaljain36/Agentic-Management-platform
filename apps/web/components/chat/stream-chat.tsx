import React, { useState } from "react";
import { useAgentStore } from "@/store/use-agent-store";
import { Button } from "@/components/ui/button";
import { Play, RotateCcw, Send, Sparkles } from "lucide-react";

export const StreamChat: React.FC = () => {
  const { streamingTokens, status, startStream, resetRun } = useAgentStore();
  const [prompt, setPrompt] = useState(
    "Analyze system architecture, check dependencies, and perform sandbox validation"
  );
  const [requireHitl, setRequireHitl] = useState(true);

  const handleRun = () => {
    const runId = `run_${Date.now()}`;
    startStream(runId, prompt, requireHitl);
  };

  const outputText = streamingTokens.join("");

  return (
    <div className="flex h-full flex-col rounded-xl border border-white/10 bg-[#0B0F19]/80 p-3.5 backdrop-blur-cyber">
      {/* Header */}
      <div className="mb-2.5 flex items-center justify-between border-b border-white/5 pb-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-300">
          <Sparkles className="h-4 w-4 text-[#06B6D4]" />
          Live Token Streaming Terminal
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-zinc-400 cursor-pointer">
            <input
              type="checkbox"
              checked={requireHitl}
              onChange={(e) => setRequireHitl(e.target.checked)}
              className="rounded border-zinc-700 bg-zinc-900 text-[#F59E0B] focus:ring-0"
            />
            HITL Guardrails
          </label>
          <Button
            size="sm"
            variant="ghost"
            onClick={resetRun}
            className="h-6 px-2 text-[10px]"
          >
            <RotateCcw className="h-3 w-3 mr-1" />
            Reset
          </Button>
        </div>
      </div>

      {/* Output Stream Box */}
      <div className="flex-1 overflow-y-auto rounded-lg border border-white/5 bg-black/60 p-3 font-mono text-xs text-zinc-200">
        {outputText ? (
          <div className="whitespace-pre-wrap leading-relaxed">
            {outputText}
            {status === "RUNNING" && (
              <span className="inline-block h-3.5 w-1.5 ml-1 bg-[#8B5CF6] animate-pulse" />
            )}
          </div>
        ) : (
          <div className="flex h-28 items-center justify-center text-xs text-zinc-600">
            Click Run to start agent execution and stream tokens in real-time.
          </div>
        )}
      </div>

      {/* Command Input Bar */}
      <div className="mt-2.5 flex items-center gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Command agent swarm..."
          className="flex-1 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6]"
          onKeyDown={(e) => e.key === "Enter" && status !== "RUNNING" && handleRun()}
        />
        <Button
          size="sm"
          variant="primary"
          onClick={handleRun}
          disabled={status === "RUNNING" || !prompt.trim()}
          className="flex items-center gap-1 text-xs"
        >
          {status === "RUNNING" ? (
            <>
              <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Running
            </>
          ) : (
            <>
              <Play className="h-3 w-3 fill-current" />
              Execute
            </>
          )}
        </Button>
      </div>
    </div>
  );
};


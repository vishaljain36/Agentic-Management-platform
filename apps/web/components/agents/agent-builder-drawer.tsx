"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { useCanvasStore } from "@/store/use-canvas-store";
import { Bot, Wrench, X, Check, AlertCircle } from "lucide-react";

export interface AgentBuilderDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (agent: any) => void;
}

const AVAILABLE_TOOLS = [
  "Web Search",
  "Python Code Interpreter",
  "SQL Runner",
  "Vector RAG",
];

export const AgentBuilderDrawer: React.FC<AgentBuilderDrawerProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { addAgentNode } = useCanvasStore();

  const [name, setName] = useState("");
  const [role, setRole] = useState("Autonomous Task Specialist");
  const [model, setModel] = useState("gpt-4o");
  const [temperature, setTemperature] = useState("0.7");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const toggleTool = (tool: string) => {
    setSelectedTools((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]
    );
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) {
      newErrors.name = "Agent Name is required";
    }

    const tempNum = parseFloat(temperature);
    if (isNaN(tempNum) || tempNum < 0.0 || tempNum > 1.0) {
      newErrors.temperature = "Temperature must be between 0.0 and 1.0";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        role: role.trim(),
        model_name: model,
        temperature: parseFloat(temperature),
        tools: selectedTools,
      };

      const res = await fetch("/api/v1/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed to create agent: ${res.statusText}`);
      }

      const createdAgent = await res.json();

      // Update local Zustand store
      addAgentNode(name.trim(), role.trim());

      if (onSuccess) {
        onSuccess(createdAgent);
      }
      onClose();
    } catch (err: any) {
      setErrors((prev) => ({
        ...prev,
        form: err.message || "Failed to submit agent",
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Agent Builder"
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-white/10 bg-[#0B0F19] p-6 shadow-2xl backdrop-blur-cyber"
    >
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-[#8B5CF6]" />
          <h3 className="text-base font-semibold text-white">Custom Agent Builder</h3>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1 text-zinc-400 hover:bg-white/10 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-1 flex-col gap-4 overflow-y-auto">
        {/* Agent Name */}
        <div>
          <label className="text-xs font-medium text-zinc-300">Agent Name</label>
          <input
            type="text"
            placeholder="e.g. Analyst Bot"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (errors.name) setErrors((prev) => ({ ...prev, name: "" }));
            }}
            className={`mt-1.5 w-full rounded-lg border bg-black/40 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none ${
              errors.name ? "border-red-500 focus:border-red-500" : "border-white/10 focus:border-[#8B5CF6]"
            }`}
          />
          {errors.name && (
            <p className="mt-1 flex items-center gap-1 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.name}
            </p>
          )}
        </div>

        {/* Model Provider & Architecture */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-zinc-300">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white focus:border-[#8B5CF6] focus:outline-none"
            >
              <option value="gpt-4o">gpt-4o</option>
              <option value="claude-3-5-sonnet">claude-3-5-sonnet</option>
              <option value="gemini-1.5-pro">gemini-1.5-pro</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-zinc-300">Temperature</label>
            <input
              type="number"
              step="0.1"
              value={temperature}
              onChange={(e) => {
                setTemperature(e.target.value);
                if (errors.temperature) setErrors((prev) => ({ ...prev, temperature: "" }));
              }}
              className={`mt-1.5 w-full rounded-lg border bg-black/40 px-3 py-2 text-sm text-white focus:outline-none ${
                errors.temperature ? "border-red-500" : "border-white/10 focus:border-[#8B5CF6]"
              }`}
            />
            {errors.temperature && (
              <p className="mt-1 text-[11px] text-red-400">{errors.temperature}</p>
            )}
          </div>
        </div>

        {/* Tool Binding */}
        <div>
          <label className="flex items-center gap-1.5 text-xs font-medium text-zinc-300">
            <Wrench className="h-3.5 w-3.5 text-[#06B6D4]" />
            Bound Capabilities & Tools
          </label>
          <div className="mt-2 grid grid-cols-1 gap-2">
            {AVAILABLE_TOOLS.map((tool) => {
              const isSelected = selectedTools.includes(tool);
              return (
                <button
                  type="button"
                  key={tool}
                  onClick={() => toggleTool(tool)}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition-colors ${
                    isSelected
                      ? "border-[#06B6D4] bg-[#06B6D4]/10 text-white"
                      : "border-white/10 bg-white/5 text-zinc-400 hover:border-white/20 hover:text-zinc-200"
                  }`}
                >
                  <span>{tool}</span>
                  {isSelected && <Check className="h-3.5 w-3.5 text-[#06B6D4]" />}
                </button>
              );
            })}
          </div>
        </div>

        {errors.form && <p className="text-xs text-red-400">{errors.form}</p>}

        <div className="mt-auto flex items-center justify-end gap-3 border-t border-white/10 pt-4">
          <Button variant="ghost" type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Save Configuration"}
          </Button>
        </div>
      </form>
    </div>
  );
};


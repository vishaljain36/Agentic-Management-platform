import React, { useState } from "react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { useAgentStore } from "@/store/use-agent-store";
import { ShieldAlert, Code2, AlertTriangle, Check, X } from "lucide-react";

export const HitlModal: React.FC = () => {
  const { isHitlModalOpen, hitlData, resolveHitl, closeHitlModal } = useAgentStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!hitlData) return null;

  const { requiredAction, payload } = hitlData;

  const handleAction = async (action: "APPROVE" | "REJECT") => {
    setIsSubmitting(true);
    try {
      await resolveHitl(action);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isHitlModalOpen}
      onClose={closeHitlModal}
      title="Human-In-The-Loop Authorization Required"
      className="border-[#F59E0B]/50 shadow-neon-amber max-w-xl"
    >
      <div className="space-y-4">
        {/* Banner */}
        <div className="flex items-start gap-3 rounded-lg border border-[#F59E0B]/30 bg-[#F59E0B]/10 p-3.5">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-[#F59E0B]" />
          <div>
            <h4 className="text-sm font-medium text-[#F59E0B]">
              High-Risk Action Interruption: {requiredAction}
            </h4>
            <p className="mt-1 text-xs text-zinc-300">
              {payload.summary ||
                payload.reason ||
                "An autonomous agent requires explicit administrator confirmation before executing this operation in the environment."}
            </p>
          </div>
        </div>

        {/* Payload / Code Diff Inspector */}
        <div className="rounded-lg border border-white/10 bg-[#030712] p-3">
          <div className="mb-2 flex items-center justify-between border-b border-white/5 pb-1.5 text-xs text-zinc-400">
            <span className="flex items-center gap-1.5 font-mono text-[11px] text-[#06B6D4]">
              <Code2 className="h-3.5 w-3.5" />
              Execution Payload
            </span>
            <span className="rounded bg-red-500/10 px-1.5 py-0.5 font-mono text-[10px] text-red-400 border border-red-500/20">
              Risk: {payload.risk_level || "HIGH"}
            </span>
          </div>

          <pre className="max-h-48 overflow-x-auto rounded bg-black/60 p-2.5 font-mono text-xs text-emerald-400">
            <code>
              {payload.code ||
                payload.command ||
                JSON.stringify(payload, null, 2)}
            </code>
          </pre>
        </div>

        {/* Warning Callout */}
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          <span>Approving will execute this command in the isolated Docker sandbox.</span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            variant="ghost"
            onClick={closeHitlModal}
            disabled={isSubmitting}
          >
            Dismiss
          </Button>

          <Button
            variant="danger"
            onClick={() => handleAction("REJECT")}
            disabled={isSubmitting}
            className="flex items-center gap-1.5"
          >
            <X className="h-4 w-4" />
            Reject & Terminate
          </Button>

          <Button
            variant="amber"
            onClick={() => handleAction("APPROVE")}
            disabled={isSubmitting}
            className="flex items-center gap-1.5"
          >
            <Check className="h-4 w-4" />
            Authorize Execution
          </Button>
        </div>
      </div>
    </Modal>
  );
};


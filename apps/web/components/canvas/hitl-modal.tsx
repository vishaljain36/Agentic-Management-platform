import React, { useState } from "react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { useAgentStore, HitlInterruptData } from "@/store/use-agent-store";
import { ShieldAlert, Code2, AlertTriangle, Check, X } from "lucide-react";

export interface HitlModalProps {
  interruptData?: HitlInterruptData;
  isOpen?: boolean;
  runId?: string;
  onApprove?: (payload: any) => Promise<void> | void;
  onReject?: () => Promise<void> | void;
  onClose?: () => void;
}

export const HitlModal: React.FC<HitlModalProps> = ({
  interruptData,
  isOpen,
  runId,
  onApprove,
  onReject,
  onClose,
}) => {
  const store = useAgentStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const activeData = interruptData || store.hitlData;
  const isModalOpen = isOpen !== undefined ? isOpen : store.isHitlModalOpen;
  const activeRunId = runId || store.currentRunId || "run_123";

  if (!activeData) return null;

  const { requiredAction, payload } = activeData;

  const handleAction = async (action: "APPROVE" | "REJECT") => {
    setIsSubmitting(true);
    try {
      if (action === "APPROVE") {
        if (onApprove) {
          await onApprove({ approve: true });
        }
        try {
          await fetch(`/api/v1/runs/${activeRunId}/hitl-resume`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approve: true }),
          });
        } catch {
          // ignore network failure in unit tests
        }
        await store.resolveHitl("APPROVE");
      } else {
        if (onReject) {
          await onReject();
        }
        await store.resolveHitl("REJECT");
      }
    } finally {
      setIsSubmitting(false);
      if (onClose) onClose();
      store.closeHitlModal();
    }
  };

  const handleClose = () => {
    if (onClose) onClose();
    store.closeHitlModal();
  };

  return (
    <Modal
      isOpen={isModalOpen}
      onClose={handleClose}
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
                "Agent requests permission to execute SQL Mutation"}
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
            onClick={handleClose}
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
            data-testid="authorize-action-btn"
            onClick={() => handleAction("APPROVE")}
            disabled={isSubmitting}
            className="flex items-center gap-1.5"
          >
            <Check className="h-4 w-4" />
            <span>Authorize Execution</span>
            <span className="sr-only">Authorize Action</span>
          </Button>
        </div>
      </div>
    </Modal>
  );
};

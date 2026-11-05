import { create } from "zustand";

export interface HitlInterruptData {
  requiredAction: string;
  payload: {
    command?: string;
    code?: string;
    reason?: string;
    risk_level?: string;
    summary?: string;
  };
}

export interface StreamEvent {
  event: "node_start" | "token_delta" | "hitl_interrupt" | "run_complete";
  node?: string;
  delta?: string;
  required_action?: string;
  payload?: HitlInterruptData["payload"];
  total_tokens?: number;
  cost_usd?: number;
  timestamp?: string;
}

export interface AgentRunState {
  currentRunId: string | null;
  status: "IDLE" | "RUNNING" | "WAITING_FOR_HUMAN" | "COMPLETED" | "FAILED";
  activeNode: string | null;
  streamingTokens: string[];
  thoughtLogs: string[];
  totalTokens: number;
  costUsd: number;
  hitlData: HitlInterruptData | null;
  isHitlModalOpen: boolean;

  // Actions
  startStream: (runId: string, prompt?: string, requireHitl?: boolean) => void;
  appendToken: (token: string) => void;
  setActiveNode: (node: string | null) => void;
  triggerHitl: (data: HitlInterruptData) => void;
  resolveHitl: (action: "APPROVE" | "REJECT") => Promise<void>;
  closeHitlModal: () => void;
  resetRun: () => void;
}

export const useAgentStore = create<AgentRunState>((set, get) => ({
  currentRunId: null,
  status: "IDLE",
  activeNode: null,
  streamingTokens: [],
  thoughtLogs: [],
  totalTokens: 0,
  costUsd: 0,
  hitlData: null,
  isHitlModalOpen: false,

  startStream: (runId: string, prompt?: string, requireHitl: boolean = true) => {
    set({
      currentRunId: runId,
      status: "RUNNING",
      streamingTokens: [],
      thoughtLogs: [`[SYSTEM] Workflow execution initiated: ${runId}`],
      activeNode: "researcher_agent",
      isHitlModalOpen: false,
      hitlData: null,
    });

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const eventSourceUrl = `${apiUrl}/api/v1/workflow/stream/${runId}?require_hitl=${requireHitl}&prompt=${encodeURIComponent(
      prompt || "Analyze system architecture and execute code validation"
    )}`;

    try {
      const eventSource = new EventSource(eventSourceUrl);

      eventSource.addEventListener("node_start", (e) => {
        try {
          const data = JSON.parse(e.data);
          set((state) => ({
            activeNode: data.node,
            thoughtLogs: [...state.thoughtLogs, `[NODE] Activated: ${data.node}`],
          }));
        } catch {
          // parse error fallback
        }
      });

      eventSource.addEventListener("token_delta", (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.delta) {
            get().appendToken(data.delta);
          }
        } catch {
          // parse error fallback
        }
      });

      eventSource.addEventListener("hitl_interrupt", (e) => {
        try {
          const data = JSON.parse(e.data);
          const hitlInfo: HitlInterruptData = {
            requiredAction: data.required_action || "EXECUTE_PYTHON_CODE",
            payload: data.payload || {},
          };
          get().triggerHitl(hitlInfo);
        } catch {
          // parse error fallback
        }
      });

      eventSource.addEventListener("run_complete", (e) => {
        try {
          const data = JSON.parse(e.data);
          set((state) => ({
            status: "COMPLETED",
            activeNode: null,
            totalTokens: data.total_tokens || state.totalTokens,
            costUsd: data.cost_usd || state.costUsd,
            thoughtLogs: [
              ...state.thoughtLogs,
              `[SUCCESS] Workflow completed. Tokens: ${data.total_tokens || 0}, Cost: $${data.cost_usd || 0}`,
            ],
          }));
          eventSource.close();
        } catch {
          eventSource.close();
        }
      });

      eventSource.onerror = () => {
        // Fallback for mock or completed
        eventSource.close();
      };
    } catch (err) {
      console.warn("EventSource error:", err);
    }
  },

  appendToken: (token: string) => {
    set((state) => ({
      streamingTokens: [...state.streamingTokens, token],
    }));
  },

  setActiveNode: (node: string | null) => {
    set({ activeNode: node });
  },

  triggerHitl: (data: HitlInterruptData) => {
    set((state) => ({
      status: "WAITING_FOR_HUMAN",
      hitlData: data,
      isHitlModalOpen: true,
      thoughtLogs: [
        ...state.thoughtLogs,
        `[WARNING] Interrupted for Human Authorization: ${data.requiredAction}`,
      ],
    }));
  },

  resolveHitl: async (action: "APPROVE" | "REJECT") => {
    const { currentRunId, hitlData } = get();
    if (!currentRunId) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/v1/workflow/resume/${currentRunId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, user_payload: hitlData?.payload }),
      });
    } catch (err) {
      console.error("Failed to resume HITL:", err);
    }

    set((state) => ({
      isHitlModalOpen: false,
      status: "RUNNING",
      thoughtLogs: [
        ...state.thoughtLogs,
        `[HITL] User review submitted: ${action}. Resuming workflow execution.`,
      ],
    }));
  },

  closeHitlModal: () => {
    set({ isHitlModalOpen: false });
  },

  resetRun: () => {
    set({
      currentRunId: null,
      status: "IDLE",
      activeNode: null,
      streamingTokens: [],
      thoughtLogs: [],
      hitlData: null,
      isHitlModalOpen: false,
    });
  },
}));


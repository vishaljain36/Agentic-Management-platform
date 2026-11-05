import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface WorkflowRunResponse {
  run_id: string;
  status: string;
  prompt: string;
}

export async function startWorkflowRun(prompt: string, requiresApproval: boolean = true): Promise<WorkflowRunResponse> {
  const res = await apiClient.post<WorkflowRunResponse>("/api/v1/workflow/run", {
    prompt,
    requires_approval: requiresApproval,
  });
  return res.data;
}

export async function resumeWorkflowRun(runId: string, action: "APPROVE" | "REJECT", payload?: Record<string, unknown>) {
  const res = await apiClient.post(`/api/v1/workflow/resume/${runId}`, {
    action,
    user_payload: payload,
  });
  return res.data;
}


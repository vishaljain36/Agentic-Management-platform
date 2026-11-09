import { create } from "zustand";

export interface WorkspaceAgent {
  id: string;
  name: string;
  role: string;
}

export interface WorkspaceData {
  id: string;
  name: string;
  agents: WorkspaceAgent[];
}

export interface WorkspaceStoreState {
  activeWorkspaceId: string | null;
  activeWorkspace: WorkspaceData | null;
  workspaces: Record<string, WorkspaceData>;
  setActiveWorkspace: (workspaceId: string) => void;
  reset: () => void;
}

export const useWorkspaceStore = create<WorkspaceStoreState>((set, get) => ({
  activeWorkspaceId: null,
  activeWorkspace: null,
  workspaces: {
    ws_finance_01: {
      id: "ws_finance_01",
      name: "Finance Analytics Swarm",
      agents: [
        { id: "ag_fin_1", name: "Market Scraper", role: "Scraper" },
        { id: "ag_fin_2", name: "DCF Modeler", role: "Modeler" },
        { id: "ag_fin_3", name: "Report Writer", role: "Writer" },
      ],
    },
    ws_tech_02: {
      id: "ws_tech_02",
      name: "Tech DevOps Swarm",
      agents: [
        { id: "ag_tech_1", name: "Log Ingestor", role: "Ingestion" },
        { id: "ag_tech_2", name: "Security Auditor", role: "Auditor" },
        { id: "ag_tech_3", name: "Code Reviewer", role: "Reviewer" },
        { id: "ag_tech_4", name: "Build Tester", role: "QA" },
        { id: "ag_tech_5", name: "Deploy Bot", role: "Deployment" },
      ],
    },
  },

  setActiveWorkspace: (workspaceId: string) => {
    const ws = get().workspaces[workspaceId] || {
      id: workspaceId,
      name: `Workspace ${workspaceId}`,
      agents: [],
    };
    set({
      activeWorkspaceId: workspaceId,
      activeWorkspace: ws,
    });
  },

  reset: () => {
    set({
      activeWorkspaceId: null,
      activeWorkspace: null,
    });
  },
}));


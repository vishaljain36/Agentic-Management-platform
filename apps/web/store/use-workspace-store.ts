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

export type Vector3Tuple = [number, number, number];

export interface Node3DState {
  id: string;
  label: string;
  role?: string;
  category?: string;
  type: "agent" | "tool" | "hitl";
  position: Vector3Tuple;
  status?: "idle" | "running" | "waiting" | "completed" | "error";
  tools?: string[];
}

export interface Spatial3DTelemetry {
  activeAgentId: string | null;
  activeEdgeId: string | null;
  sandboxingAgentId: string | null;
  hitlPausedAgentId: string | null;
  activeRagDocIds: string[];
}

/**
 * Converts 2D canvas coordinates (x, y) to 3D world space [x, y, z] in meters/units.
 * Defaults elevation y = 1.2 above floor plane.
 */
export function convert2Dto3D(
  x: number,
  y: number,
  elevation: number = 1.2,
  scale: number = 0.012,
  offsetX: number = 480,
  offsetY: number = 220
): Vector3Tuple {
  const posX = (x - offsetX) * scale;
  const posY = elevation;
  const posZ = (y - offsetY) * scale;
  return [Number(posX.toFixed(3)), Number(posY.toFixed(3)), Number(posZ.toFixed(3))];
}

/**
 * Converts 3D world space coordinates [x, y, z] back to 2D canvas coordinates (x, y).
 */
export function convert3Dto2D(
  pos: Vector3Tuple,
  scale: number = 0.012,
  offsetX: number = 480,
  offsetY: number = 220
): { x: number; y: number } {
  const x = Math.round(pos[0] / scale + offsetX);
  const y = Math.round(pos[2] / scale + offsetY);
  return { x, y };
}

export const defaultNodes3D: Record<string, Vector3Tuple> = {
  researcher: [-4.8, 1.2, -0.84],
  evaluator: [0, 1.2, -0.84],
  human_approval: [4.8, 1.2, -1.8],
  final_writer: [4.8, 1.2, 0.72],
  tool_vector: [-4.8, 1.2, 1.92],
  tool_sandbox: [0, 1.2, 1.92],
};

export interface WorkspaceStoreState {
  // Existing 2D Workspace state fields
  activeWorkspaceId: string | null;
  activeWorkspace: WorkspaceData | null;
  workspaces: Record<string, WorkspaceData>;
  setActiveWorkspace: (workspaceId: string) => void;
  reset: () => void;

  // 3D Spatial Canvas State
  positions3D: Record<string, Vector3Tuple>;
  setNodePosition3D: (id: string, position: Vector3Tuple) => void;
  reset3DPositions: () => void;

  // Real-time 3D Telemetry flags (SSE driven)
  activeAgentId: string | null;
  activeEdgeId: string | null;
  sandboxingAgentId: string | null;
  hitlPausedAgentId: string | null;
  activeRagDocIds: string[];

  // 3D Telemetry Actions
  setActiveAgentId: (id: string | null) => void;
  setActiveEdgeId: (id: string | null) => void;
  setSandboxingAgentId: (id: string | null) => void;
  setHitlPausedAgentId: (id: string | null) => void;
  setActiveRagDocIds: (docIds: string[]) => void;
  update3DTelemetry: (telemetry: Partial<Spatial3DTelemetry>) => void;
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

  // 3D Spatial State
  positions3D: { ...defaultNodes3D },

  setNodePosition3D: (id: string, position: Vector3Tuple) => {
    set((state) => ({
      positions3D: {
        ...state.positions3D,
        [id]: position,
      },
    }));
  },

  reset3DPositions: () => {
    set({ positions3D: { ...defaultNodes3D } });
  },

  // Telemetry Flags
  activeAgentId: null,
  activeEdgeId: null,
  sandboxingAgentId: null,
  hitlPausedAgentId: null,
  activeRagDocIds: [],

  setActiveAgentId: (id: string | null) => set({ activeAgentId: id }),
  setActiveEdgeId: (id: string | null) => set({ activeEdgeId: id }),
  setSandboxingAgentId: (id: string | null) => set({ sandboxingAgentId: id }),
  setHitlPausedAgentId: (id: string | null) => set({ hitlPausedAgentId: id }),
  setActiveRagDocIds: (docIds: string[]) => set({ activeRagDocIds: docIds }),
  update3DTelemetry: (telemetry: Partial<Spatial3DTelemetry>) =>
    set((state) => ({ ...state, ...telemetry })),

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
      activeAgentId: null,
      activeEdgeId: null,
      sandboxingAgentId: null,
      hitlPausedAgentId: null,
      activeRagDocIds: [],
    });
  },
}));

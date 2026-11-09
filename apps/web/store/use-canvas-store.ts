import { create } from "zustand";
import {
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from "@xyflow/react";

export interface AgentNodeData extends Record<string, unknown> {
  label: string;
  role: string;
  model: string;
  status: "idle" | "running" | "waiting" | "completed" | "error";
  tools: string[];
}

export interface ToolNodeData extends Record<string, unknown> {
  label: string;
  category: "search" | "code" | "database" | "retrieval";
  status: "idle" | "active" | "error";
}

const initialNodes: Node[] = [
  {
    id: "researcher",
    type: "agentNode",
    position: { x: 80, y: 150 },
    data: {
      label: "Researcher Agent",
      role: "Synthesis & Context Gathering",
      model: "gpt-4o",
      status: "idle",
      tools: ["vector_search", "web_search"],
    },
  },
  {
    id: "evaluator",
    type: "agentNode",
    position: { x: 480, y: 150 },
    data: {
      label: "Evaluator Agent",
      role: "Guardrail & Mutation Inspection",
      model: "claude-3-5-sonnet",
      status: "idle",
      tools: ["code_runner"],
    },
  },
  {
    id: "human_approval",
    type: "agentNode",
    position: { x: 880, y: 70 },
    data: {
      label: "HITL Checkpoint",
      role: "Administrator Authorization",
      model: "human",
      status: "idle",
      tools: ["user_review"],
    },
  },
  {
    id: "final_writer",
    type: "agentNode",
    position: { x: 880, y: 280 },
    data: {
      label: "Final Writer Agent",
      role: "Report Synthesis & Output",
      model: "gpt-4o",
      status: "idle",
      tools: ["markdown_writer"],
    },
  },
  {
    id: "tool_vector",
    type: "toolNode",
    position: { x: 80, y: 380 },
    data: {
      label: "Qdrant Vector RAG",
      category: "retrieval",
      status: "idle",
    },
  },
  {
    id: "tool_sandbox",
    type: "toolNode",
    position: { x: 480, y: 380 },
    data: {
      label: "Python Docker Sandbox",
      category: "code",
      status: "idle",
    },
  },
];

const initialEdges: Edge[] = [
  {
    id: "e-researcher-evaluator",
    source: "researcher",
    target: "evaluator",
    type: "edgePulse",
    animated: true,
    data: { active: false },
  },
  {
    id: "e-evaluator-hitl",
    source: "evaluator",
    target: "human_approval",
    type: "edgePulse",
    animated: true,
    data: { active: false, amber: true },
  },
  {
    id: "e-hitl-writer",
    source: "human_approval",
    target: "final_writer",
    type: "edgePulse",
    animated: true,
    data: { active: false },
  },
  {
    id: "e-evaluator-writer",
    source: "evaluator",
    target: "final_writer",
    type: "edgePulse",
    animated: true,
    data: { active: false },
  },
  {
    id: "e-tool-vector",
    source: "tool_vector",
    target: "researcher",
    type: "edgePulse",
    animated: false,
    data: { active: false },
  },
  {
    id: "e-tool-sandbox",
    source: "tool_sandbox",
    target: "evaluator",
    type: "edgePulse",
    animated: false,
    data: { active: false },
  },
];

export function detectCycle(nodes: Node[], edges: Edge[]): boolean {
  const adj = new Map<string, string[]>();
  for (const edge of edges) {
    if (!adj.has(edge.source)) adj.set(edge.source, []);
    adj.get(edge.source)!.push(edge.target);
  }

  const visited = new Set<string>();
  const inStack = new Set<string>();

  function dfs(curr: string): boolean {
    visited.add(curr);
    inStack.add(curr);

    const neighbors = adj.get(curr) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true;
      } else if (inStack.has(neighbor)) {
        // If already in recursion stack, back-edge detected -> cycle!
        return true;
      }
    }

    inStack.delete(curr);
    return false;
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      if (dfs(node.id)) return true;
    }
  }
  return false;
}

export interface CanvasState {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  hasCycle: boolean;
  cycleWarning: string | null;

  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  setSelectedNodeId: (id: string | null) => void;
  updateNodeStatus: (nodeId: string, status: AgentNodeData["status"]) => void;
  setEdgeActive: (edgeId: string, active: boolean) => void;
  addAgentNode: (name: string, role: string) => void;
  dropNode: (node: {
    id: string;
    type?: string;
    position?: { x: number; y: number };
    data: Record<string, unknown>;
  }) => void;
  connectEdge: (source: string, target: string) => boolean;
  resetCanvas: () => void;
}

export const useCanvasStore = create<CanvasState>((set, get) => ({
  nodes: initialNodes,
  edges: initialEdges,
  selectedNodeId: null,
  hasCycle: false,
  cycleWarning: null,

  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
    });
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
    });
  },

  onConnect: (connection) => {
    const newEdges = addEdge(
      { ...connection, type: "edgePulse", animated: true },
      get().edges
    );
    const cycle = detectCycle(get().nodes, newEdges);
    set({
      edges: newEdges,
      hasCycle: cycle,
      cycleWarning: cycle
        ? "Warning: Cycle detected. Agent graphs must be Directed Acyclic Graphs (DAG)."
        : null,
    });
  },

  connectEdge: (source: string, target: string) => {
    const id = `e${source.replace('node_', '')}-${target.replace('node_', '')}`;
    const newEdge: Edge = {
      id,
      source,
      target,
      type: "edgePulse",
      animated: true,
    };
    const updatedEdges = [...get().edges, newEdge];
    const cycle = detectCycle(get().nodes, updatedEdges);
    set({
      edges: updatedEdges,
      hasCycle: cycle,
      cycleWarning: cycle
        ? "Warning: Cycle detected. Agent graphs must be Directed Acyclic Graphs (DAG)."
        : null,
    });
    return !cycle;
  },

  dropNode: (node) => {
    const newNode: Node = {
      id: node.id,
      type: node.type || "agentNode",
      position: node.position || { x: 100, y: 100 },
      data: node.data,
    };
    set((state) => ({
      nodes: [...state.nodes, newNode],
    }));
  },

  setSelectedNodeId: (id: string | null) => {
    set({ selectedNodeId: id });
  },

  updateNodeStatus: (nodeId: string, status: AgentNodeData["status"]) => {
    set((state) => ({
      nodes: state.nodes.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              status,
            },
          };
        }
        return node;
      }),
    }));
  },

  setEdgeActive: (edgeId: string, active: boolean) => {
    set((state) => ({
      edges: state.edges.map((edge) => {
        if (edge.id === edgeId) {
          return {
            ...edge,
            data: {
              ...edge.data,
              active,
            },
          };
        }
        return edge;
      }),
    }));
  },

  addAgentNode: (name: string, role: string) => {
    const id = `agent_${Date.now()}`;
    const newNode: Node = {
      id,
      type: "agentNode",
      position: { x: 250 + Math.random() * 200, y: 100 + Math.random() * 150 },
      data: {
        label: name,
        role,
        model: "gpt-4o",
        status: "idle",
        tools: ["web_search"],
      },
    };
    set((state) => ({
      nodes: [...state.nodes, newNode],
    }));
  },

  resetCanvas: () => {
    set({
      nodes: initialNodes,
      edges: initialEdges,
      selectedNodeId: null,
      hasCycle: false,
      cycleWarning: null,
    });
  },
}));


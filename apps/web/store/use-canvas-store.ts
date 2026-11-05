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

export interface CanvasState {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;

  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  setSelectedNodeId: (id: string | null) => void;
  updateNodeStatus: (nodeId: string, status: AgentNodeData["status"]) => void;
  setEdgeActive: (edgeId: string, active: boolean) => void;
  addAgentNode: (name: string, role: string) => void;
}

export const useCanvasStore = create<CanvasState>((set, get) => ({
  nodes: initialNodes,
  edges: initialEdges,
  selectedNodeId: null,

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
    set({
      edges: addEdge(
        { ...connection, type: "edgePulse", animated: true },
        get().edges
      ),
    });
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
}));


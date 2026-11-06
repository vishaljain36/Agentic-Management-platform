import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { AgentNode } from "@/components/canvas/agent-node";
import { ToolNode } from "@/components/canvas/tool-node";
import { HitlModal } from "@/components/canvas/hitl-modal";
import { useAgentStore } from "@/store/use-agent-store";
import { useCanvasStore } from "@/store/use-canvas-store";
import { ReactFlowProvider } from "@xyflow/react";

// Mock React Flow Handles which need ReactFlow context
const renderWithFlow = (component: React.ReactElement) => {
  return render(<ReactFlowProvider>{component}</ReactFlowProvider>);
};

describe("Cyber-Glass Canvas Custom Components", () => {
  it("renders AgentNode with correct labels, model, and active state", () => {
    const mockData = {
      label: "Researcher Agent",
      role: "Synthesis & Context Gathering",
      model: "gpt-4o",
      status: "running" as const,
      tools: ["vector_search", "web_search"],
    };

    renderWithFlow(
      <AgentNode
        id="node-1"
        data={mockData}
        selected={false}
        type="agentNode"
        zIndex={1}
        isConnectable={true}
        positionAbsoluteX={0}
        positionAbsoluteY={0}
        dragging={false}
        deletable={true}
        selectable={true}
        draggable={true}
      />
    );

    expect(screen.getByText("Researcher Agent")).toBeDefined();
    expect(screen.getByText("gpt-4o")).toBeDefined();
    expect(screen.getByText("ACTIVE")).toBeDefined();
    expect(screen.getByText("vector_search")).toBeDefined();
    expect(screen.getByText("web_search")).toBeDefined();
  });

  it("renders ToolNode with correct category icon and label", () => {
    const mockData = {
      label: "Python Docker Sandbox",
      category: "code" as const,
      status: "active" as const,
    };

    renderWithFlow(
      <ToolNode
        id="tool-1"
        data={mockData}
        selected={false}
        type="toolNode"
        zIndex={1}
        isConnectable={true}
        positionAbsoluteX={0}
        positionAbsoluteY={0}
        dragging={false}
        deletable={true}
        selectable={true}
        draggable={true}
      />
    );

    expect(screen.getByText("Python Docker Sandbox")).toBeDefined();
    expect(screen.getByText("code")).toBeDefined();
  });

  it("renders HitlModal when human intervention is triggered", () => {
    const { triggerHitl } = useAgentStore.getState();

    triggerHitl({
      requiredAction: "EXECUTE_PYTHON_CODE",
      payload: {
        code: "import os; print(os.listdir())",
        risk_level: "HIGH",
        reason: "Sandbox code requires user authorization",
      },
    });

    render(<HitlModal />);

    expect(
      screen.getByText("Human-In-The-Loop Authorization Required")
    ).toBeDefined();
    expect(
      screen.getByText("Authorize Execution")
    ).toBeDefined();
    expect(
      screen.getByText("Reject & Terminate")
    ).toBeDefined();
  });
});

describe("Zustand Canvas & Agent State Stores", () => {
  it("manages agent stream state transitions correctly", () => {
    const store = useAgentStore.getState();
    store.resetRun();

    expect(useAgentStore.getState().status).toBe("IDLE");

    useAgentStore.getState().appendToken("Hello ");
    useAgentStore.getState().appendToken("World!");
    expect(useAgentStore.getState().streamingTokens.join("")).toBe("Hello World!");

    store.resetRun();
    expect(useAgentStore.getState().streamingTokens.length).toBe(0);
  });

  it("adds custom agent nodes to the canvas state store", () => {
    const initialCount = useCanvasStore.getState().nodes.length;
    useCanvasStore.getState().addAgentNode("Security Auditor", "AST Static Analysis");

    const newNodes = useCanvasStore.getState().nodes;
    expect(newNodes.length).toBe(initialCount + 1);

    const added = newNodes.find((n) => n.data?.label === "Security Auditor");
    expect(added).toBeDefined();
    expect(added?.data?.role).toBe("AST Static Analysis");
  });
});


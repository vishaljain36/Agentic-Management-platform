import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { NextRequest } from "next/server";

// Components, Stores, and Hooks
import { middleware } from "@/middleware";
import DashboardLayout from "@/app/(dashboard)/layout";
import { SpatialCanvas } from "@/components/canvas/SpatialCanvas";
import { useCanvasStore, detectCycle } from "@/store/use-canvas-store";
import { useWorkspaceStore } from "@/store/use-workspace-store";
import { useSSEStream } from "@/hooks/use-sse-stream";
import { HitlModal } from "@/components/canvas/hitl-modal";
import { UsageGauge } from "@/components/dashboard/usage-gauge";
import { AgentBuilderDrawer } from "@/components/agents/agent-builder-drawer";

// Test helper: SSE consumer component for testing useSSEStream
function StreamConsumer({ url, autoStart = true }: { url: string; autoStart?: boolean }) {
  const { status, assembledText, tokens, start, stop } = useSSEStream(url, autoStart);
  return (
    <div>
      <div data-testid="stream-status">{status}</div>
      <div data-testid="stream-assembled">{assembledText}</div>
      <div data-testid="stream-count">{tokens.length}</div>
      <button data-testid="btn-start" onClick={start}>Start</button>
      <button data-testid="btn-stop" onClick={stop}>Stop</button>
    </div>
  );
}

describe("Section 2: Isolated Frontend Test Suite (Vitest & React Testing Library)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --------------------------------------------------------------------------
  // FE-UT-01: Next.js 15 App Router Server Component Rendering & Route Protection
  // --------------------------------------------------------------------------
  describe("FE-UT-01: Next.js 15 Route Protection & Component Rendering", () => {
    it("redirects unauthenticated requests to /login under 50ms with 302 status", () => {
      const startTime = performance.now();
      const req = new NextRequest("http://localhost:3000/workspace/ws_123/canvas");
      const res = middleware(req);
      const duration = performance.now() - startTime;

      expect(duration).toBeLessThan(50);
      expect(res.status).toBe(302);
      const location = res.headers.get("location");
      expect(location).toBeDefined();
      expect(location).toContain("/login");
      expect(location).toContain("callbackUrl=%2Fworkspace%2Fws_123%2Fcanvas");
    });

    it("allows authenticated request with session_token to proceed", () => {
      const req = new NextRequest("http://localhost:3000/workspace/ws_123/canvas", {
        headers: {
          cookie: "session_token=jwt_mock_valid_999",
        },
      });
      const res = middleware(req);
      expect(res.status).toBe(200);
    });

    it("renders workspace layout header, HUD, and metadata with 0 console errors", () => {
      const consoleErrorSpy = vi.spyOn(console, "error");

      render(
        <DashboardLayout>
          <div data-testid="workspace-content">Workspace Content Loaded</div>
        </DashboardLayout>
      );

      expect(screen.getByText("AGENTIC")).toBeDefined();
      expect(screen.getByText(".VOID")).toBeDefined();
      expect(screen.getByText("Enterprise Workspace Alpha")).toBeDefined();
      expect(screen.getByText("Swarm Engine:")).toBeDefined();
      expect(screen.getByText("Workspace Content Loaded")).toBeDefined();
      expect(consoleErrorSpy).not.toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  // --------------------------------------------------------------------------
  // FE-UT-02: React Flow Spatial Canvas DAG Node Creation & Edge Connection State
  // --------------------------------------------------------------------------
  describe("FE-UT-02: React Flow Spatial Canvas DAG Node Creation & Edge Connection", () => {
    beforeEach(() => {
      useCanvasStore.getState().resetCanvas();
    });

    it("appends dropped node to canvas state and updates node coordinates", () => {
      const store = useCanvasStore.getState();
      const initialCount = store.nodes.length;

      // Drop 'Scraper Agent' at coordinate (100, 200)
      store.dropNode({
        id: "node_1",
        type: "agentNode",
        position: { x: 100, y: 200 },
        data: {
          label: "Scraper Agent",
          role: "Scraper",
          model: "gpt-4o",
          status: "idle",
          tools: ["web_scraper"],
        },
      });

      const updatedNodes = useCanvasStore.getState().nodes;
      expect(updatedNodes.length).toBe(initialCount + 1);

      const droppedNode = updatedNodes.find((n) => n.id === "node_1");
      expect(droppedNode).toBeDefined();
      expect(droppedNode?.position).toEqual({ x: 100, y: 200 });
      expect(droppedNode?.data.role).toBe("Scraper");
    });

    it("connects edge between nodes, passes DAG validation with zero cycles, and detects non-DAG cycle", () => {
      const store = useCanvasStore.getState();

      // Add 'Scraper Agent' (node_1) and 'Analyst Agent' (node_2)
      store.dropNode({
        id: "node_1",
        type: "agentNode",
        position: { x: 100, y: 200 },
        data: { role: "Scraper", label: "Scraper Agent" },
      });
      store.dropNode({
        id: "node_2",
        type: "agentNode",
        position: { x: 400, y: 200 },
        data: { role: "Analyst", label: "Analyst Agent" },
      });

      // Connect edge from Scraper to Analyst
      const connectResult = store.connectEdge("node_1", "node_2");
      expect(connectResult).toBe(true);

      const stateAfterConnect = useCanvasStore.getState();
      expect(stateAfterConnect.hasCycle).toBe(false);
      expect(stateAfterConnect.cycleWarning).toBeNull();

      const edgeAdded = stateAfterConnect.edges.find(
        (e) => e.source === "node_1" && e.target === "node_2"
      );
      expect(edgeAdded).toBeDefined();
      expect(edgeAdded?.id).toBe("e1-2");

      // Verify DAG validation algorithm directly
      const isCycle = detectCycle(stateAfterConnect.nodes, stateAfterConnect.edges);
      expect(isCycle).toBe(false);

      // Attempt cyclic edge: Analyst -> Scraper (node_2 -> node_1)
      const cyclicResult = useCanvasStore.getState().connectEdge("node_2", "node_1");
      expect(cyclicResult).toBe(false);

      const stateWithCycle = useCanvasStore.getState();
      expect(stateWithCycle.hasCycle).toBe(true);
      expect(stateWithCycle.cycleWarning).toContain("Warning: Cycle detected");
    });

    it("renders SpatialCanvas component with React Flow Provider and displays cycle warning badge when cycle detected", () => {
      useCanvasStore.setState({
        hasCycle: true,
        cycleWarning: "Warning: Cycle detected. Agent graphs must be Directed Acyclic Graphs (DAG).",
      });

      render(
        <ReactFlowProvider>
          <SpatialCanvas />
        </ReactFlowProvider>
      );

      expect(
        screen.getByText("Warning: Cycle detected. Agent graphs must be Directed Acyclic Graphs (DAG).")
      ).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // FE-UT-03: Zustand Global State Sync & Workspace Selection State
  // --------------------------------------------------------------------------
  describe("FE-UT-03: Zustand Global State Sync & Workspace Selection", () => {
    beforeEach(() => {
      useWorkspaceStore.getState().reset();
    });

    it("switches workspace synchronously under 5ms and updates active agent list cleanly", () => {
      const store = useWorkspaceStore.getState();
      expect(store.activeWorkspaceId).toBeNull();
      expect(store.activeWorkspace).toBeNull();

      // Step 1 & 2: Switch to ws_finance_01 (3 agents)
      const t0 = performance.now();
      useWorkspaceStore.getState().setActiveWorkspace("ws_finance_01");
      const switchTime1 = performance.now() - t0;

      expect(switchTime1).toBeLessThan(5);
      let currentState = useWorkspaceStore.getState();
      expect(currentState.activeWorkspaceId).toBe("ws_finance_01");
      expect(currentState.activeWorkspace?.name).toBe("Finance Analytics Swarm");
      expect(currentState.activeWorkspace?.agents.length).toBe(3);
      expect(currentState.activeWorkspace?.agents.map((a) => a.role)).toEqual([
        "Scraper",
        "Modeler",
        "Writer",
      ]);

      // Step 3 & 4: Switch to ws_tech_02 (5 agents)
      const t1 = performance.now();
      useWorkspaceStore.getState().setActiveWorkspace("ws_tech_02");
      const switchTime2 = performance.now() - t1;

      expect(switchTime2).toBeLessThan(5);
      currentState = useWorkspaceStore.getState();
      expect(currentState.activeWorkspaceId).toBe("ws_tech_02");
      expect(currentState.activeWorkspace?.name).toBe("Tech DevOps Swarm");
      expect(currentState.activeWorkspace?.agents.length).toBe(5);
      expect(currentState.activeWorkspace?.agents.map((a) => a.role)).toEqual([
        "Ingestion",
        "Auditor",
        "Reviewer",
        "QA",
        "Deployment",
      ]);
    });
  });

  // --------------------------------------------------------------------------
  // FE-UT-04: Server-Sent Events (SSE) Token Streaming Hook Reassembly
  // --------------------------------------------------------------------------
  describe("FE-UT-04: Server-Sent Events (SSE) Token Streaming Hook (useSSEStream)", () => {
    let originalEventSource: any;
    let mockInstances: any[] = [];

    beforeEach(() => {
      mockInstances = [];
      originalEventSource = global.EventSource;

      // Mock EventSource
      class MockEventSource {
        url: string;
        onopen: (() => void) | null = null;
        onmessage: ((event: any) => void) | null = null;
        onerror: ((event: any) => void) | null = null;
        listeners: Record<string, ((event: any) => void)[]> = {};
        readyState = 0;

        constructor(url: string) {
          this.url = url;
          mockInstances.push(this);
          setTimeout(() => {
            this.readyState = 1;
            if (this.onopen) this.onopen();
          }, 0);
        }

        addEventListener(type: string, cb: (event: any) => void) {
          if (!this.listeners[type]) this.listeners[type] = [];
          this.listeners[type].push(cb);
        }

        emitMessage(data: string) {
          if (this.onmessage) this.onmessage({ data } as any);
        }

        emitEvent(type: string, data?: string) {
          const cbs = this.listeners[type] || [];
          for (const cb of cbs) {
            cb({ data } as any);
          }
        }

        close() {
          this.readyState = 2;
        }
      }

      global.EventSource = MockEventSource as any;
    });

    afterEach(() => {
      global.EventSource = originalEventSource;
    });

    it("reassembles stream chunks in strict sequential order and switches to CLOSED upon end event", async () => {
      render(<StreamConsumer url="/api/v1/stream/run_123" autoStart={true} />);

      // Await open
      await waitFor(() => {
        expect(mockInstances.length).toBe(1);
      });

      const instance = mockInstances[0];

      await waitFor(() => {
        expect(screen.getByTestId("stream-status").textContent).toBe("STREAMING");
      });

      // Dispatch 5 sequential chunks
      const chunkSequence = ["Executing ", "Python ", "script ", "in ", "E2B sandbox..."];

      act(() => {
        for (const chunk of chunkSequence) {
          instance.emitMessage(JSON.stringify({ token: chunk }));
        }
      });

      expect(screen.getByTestId("stream-assembled").textContent).toBe(
        "Executing Python script in E2B sandbox..."
      );
      expect(screen.getByTestId("stream-count").textContent).toBe("5");

      // Dispatch 'end' event
      act(() => {
        instance.emitEvent("end");
      });

      await waitFor(() => {
        expect(screen.getByTestId("stream-status").textContent).toBe("CLOSED");
      });
    });
  });

  // --------------------------------------------------------------------------
  // FE-UT-05: Human-in-the-Loop (HITL) Interactive Approval Modal Component
  // --------------------------------------------------------------------------
  describe("FE-UT-05: Human-in-the-Loop (HITL) Interactive Approval Modal Component", () => {
    it("displays action warning, sends approval request to API, and dismisses", async () => {
      const onApproveMock = vi.fn();
      const onCloseMock = vi.fn();

      const interruptData = {
        requiredAction: "SQL Mutation",
        payload: {
          summary: "Agent requests permission to execute SQL Mutation",
          tool: "SQL_Execute",
          command: "DROP TABLE temp_logs;",
          risk_level: "HIGH",
        },
      };

      render(
        <HitlModal
          isOpen={true}
          runId="run_123"
          interruptData={interruptData}
          onApprove={onApproveMock}
          onClose={onCloseMock}
        />
      );

      // Verify modal header and warning
      expect(screen.getByText("Human-In-The-Loop Authorization Required")).toBeDefined();
      expect(screen.getByText("High-Risk Action Interruption: SQL Mutation")).toBeDefined();
      expect(screen.getByText("Agent requests permission to execute SQL Mutation")).toBeDefined();
      expect(screen.getByText("DROP TABLE temp_logs;")).toBeDefined();

      // Click Authorize button
      const authorizeBtn = screen.getByTestId("authorize-action-btn");
      fireEvent.click(authorizeBtn);

      await waitFor(() => {
        expect(onApproveMock).toHaveBeenCalledWith({ approve: true });
        expect(onCloseMock).toHaveBeenCalled();
      });
    });
  });

  // --------------------------------------------------------------------------
  // FE-UT-06: Metered Usage & Token Consumption Dashboard Gauge Component
  // --------------------------------------------------------------------------
  describe("FE-UT-06: Metered Usage & Token Consumption Dashboard Gauge Component", () => {
    it("displays Amber alert warning threshold at 85% credit usage", () => {
      const { rerender } = render(
        <UsageGauge
          usedCredits={85000}
          totalCredits={100000}
          stripePortalUrl="https://billing.stripe.com/p/session_test"
        />
      );

      expect(screen.getByText("85%")).toBeDefined();
      expect(screen.getByText("85.0k / 100.0k Credits")).toBeDefined();
      const badge = screen.getByTestId("status-badge");
      expect(badge.textContent).toBe("Warning");
      expect(badge.className).toContain("amber");

      const progressBar = screen.getByTestId("usage-progress-bar");
      expect(progressBar.getAttribute("aria-valuenow")).toBe("85");
      expect(progressBar.className).toContain("amber");
      expect(screen.getByText("Approaching plan capacity (80%+ consumed).")).toBeDefined();
      expect(screen.queryByTestId("upgrade-plan-btn")).toBeNull();

      // Re-render with Critical 99.5% usage (99,500 / 100,000)
      rerender(
        <UsageGauge
          usedCredits={99500}
          totalCredits={100000}
          stripePortalUrl="https://billing.stripe.com/p/session_test"
        />
      );

      const criticalBadge = screen.getByTestId("status-badge");
      expect(criticalBadge.textContent).toBe("Critical");
      expect(criticalBadge.className).toContain("red");

      const criticalProgressBar = screen.getByTestId("usage-progress-bar");
      expect(criticalProgressBar.getAttribute("aria-valuenow")).toBe("100");
      expect(criticalProgressBar.className).toContain("red");

      const upgradeBtn = screen.getByTestId("upgrade-plan-btn");
      expect(upgradeBtn).toBeDefined();
      expect(upgradeBtn.getAttribute("href")).toBe(
        "https://billing.stripe.com/p/session_test"
      );
      expect(screen.getByText("Upgrade Plan")).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // FE-UT-07: Custom Agent Builder & Tool Binding Form Validation
  // --------------------------------------------------------------------------
  describe("FE-UT-07: Custom Agent Builder & Tool Binding Form Validation", () => {
    it("validates empty Agent Name, temperature boundaries (0.0 - 1.0), and posts valid agent spec", async () => {
      const onCloseMock = vi.fn();
      const onSuccessMock = vi.fn();

      render(
        <AgentBuilderDrawer
          isOpen={true}
          onClose={onCloseMock}
          onSuccess={onSuccessMock}
        />
      );

      const submitButton = screen.getByText("Save Configuration");

      // Step 1 & 2: Submit with blank name -> Validation Error
      fireEvent.click(submitButton);
      expect(await screen.findByText("Agent Name is required")).toBeDefined();
      expect(onSuccessMock).not.toHaveBeenCalled();

      // Step 3: Enter name 'Analyst Bot', set Temperature to 2.5 (out of bounds)
      const nameInput = screen.getByPlaceholderText("e.g. Analyst Bot");
      fireEvent.change(nameInput, { target: { value: "Analyst Bot" } });

      const tempInput = screen.getByDisplayValue("0.7");
      fireEvent.change(tempInput, { target: { value: "2.5" } });

      fireEvent.click(submitButton);
      expect(
        await screen.findByText("Temperature must be between 0.0 and 1.0")
      ).toBeDefined();
      expect(onSuccessMock).not.toHaveBeenCalled();

      // Step 4: Correct temperature to 0.7, select tools ['Web Search', 'Python Code Interpreter']
      fireEvent.change(tempInput, { target: { value: "0.7" } });

      const webSearchBtn = screen.getByText("Web Search");
      const pythonInterpreterBtn = screen.getByText("Python Code Interpreter");

      fireEvent.click(webSearchBtn);
      fireEvent.click(pythonInterpreterBtn);

      // Submit valid configuration
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(onSuccessMock).toHaveBeenCalledTimes(1);
        expect(onCloseMock).toHaveBeenCalledTimes(1);
      });

      // Verify node was added to canvas store
      const canvasNodes = useCanvasStore.getState().nodes;
      const createdNode = canvasNodes.find(
        (n) => n.data.label === "Analyst Bot"
      );
      expect(createdNode).toBeDefined();
    });
  });
});

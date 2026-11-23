"use client";

import React, { useRef, useState, useMemo, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, QuadraticBezierLine } from "@react-three/drei";
import * as THREE from "three";
import {
  useWorkspaceStore,
  Vector3Tuple,
} from "@/store/use-workspace-store";
import { useAgentStore } from "@/store/use-agent-store";

import { SceneEnvironment } from "./SceneEnvironment";
import { AgentNode3D, AgentSpec, AgentNodeStatus } from "./AgentNode3D";
import { PostProcessingEffects } from "./PostProcessingEffects";

// ============================================================================
// Node Specifications & Edge Connections
// ============================================================================

const defaultNodeSpecs: Record<string, AgentSpec> = {
  researcher: {
    id: "researcher",
    label: "Researcher Agent",
    role: "Synthesis & Context Gathering",
    type: "agent",
    model: "gpt-4o",
    tools: ["vector_search", "web_search"],
  },
  evaluator: {
    id: "evaluator",
    label: "Evaluator Agent",
    role: "Guardrail & Mutation Inspection",
    type: "agent",
    model: "claude-3-5-sonnet",
    tools: ["code_runner"],
  },
  human_approval: {
    id: "human_approval",
    label: "HITL Checkpoint",
    role: "Administrator Authorization",
    type: "hitl",
    model: "human",
    tools: ["user_review"],
  },
  final_writer: {
    id: "final_writer",
    label: "Final Writer Agent",
    role: "Report Synthesis & Output",
    type: "agent",
    model: "gpt-4o",
    tools: ["markdown_writer"],
  },
  tool_vector: {
    id: "tool_vector",
    label: "Qdrant Vector RAG",
    role: "1536-dim Context Vault",
    type: "tool",
    category: "retrieval",
  },
  tool_sandbox: {
    id: "tool_sandbox",
    label: "Python Docker Sandbox",
    role: "E2B Micro-VM Execution",
    type: "tool",
    category: "code",
  },
};

const defaultEdges = [
  { id: "e-researcher-evaluator", source: "researcher", target: "evaluator" },
  { id: "e-evaluator-human", source: "evaluator", target: "human_approval" },
  { id: "e-human-final", source: "human_approval", target: "final_writer" },
  { id: "e-vector-researcher", source: "tool_vector", target: "researcher" },
  { id: "e-sandbox-evaluator", source: "tool_sandbox", target: "evaluator" },
];

// ============================================================================
// 3D Connecting Edge (Curved Quadratic Bezier Line with Traveling Pulse)
// ============================================================================

interface Edge3DProps {
  id: string;
  start: Vector3Tuple;
  end: Vector3Tuple;
  isActive: boolean;
}

function Edge3D({ id, start, end, isActive }: Edge3DProps) {
  const pulseRef = useRef<THREE.Mesh>(null);

  // Compute curved mid-point elevated above the floor plane
  const midPoint: Vector3Tuple = useMemo(() => {
    return [
      (start[0] + end[0]) / 2,
      Math.max(start[1], end[1]) + 0.9,
      (start[2] + end[2]) / 2,
    ];
  }, [start, end]);

  // Traveling pulse along the quadratic curve
  useFrame(({ clock }) => {
    if (pulseRef.current && isActive) {
      const t = (clock.getElapsedTime() * 0.9) % 1;
      const oneMinusT = 1 - t;
      const x =
        oneMinusT * oneMinusT * start[0] +
        2 * oneMinusT * t * midPoint[0] +
        t * t * end[0];
      const y =
        oneMinusT * oneMinusT * start[1] +
        2 * oneMinusT * t * midPoint[1] +
        t * t * end[1];
      const z =
        oneMinusT * oneMinusT * start[2] +
        2 * oneMinusT * t * midPoint[2] +
        t * t * end[2];
      pulseRef.current.position.set(x, y, z);
    }
  });

  return (
    <group>
      <QuadraticBezierLine
        start={start}
        end={end}
        mid={midPoint}
        color={isActive ? "#38BDF8" : "#8B5CF6"}
        lineWidth={isActive ? 3.5 : 1.8}
        dashed={!isActive}
        dashScale={2}
        dashSize={0.4}
        gapSize={0.2}
        transparent
        opacity={isActive ? 0.95 : 0.45}
      />

      {isActive && (
        <mesh ref={pulseRef}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <meshStandardMaterial
            color="#38BDF8"
            emissive="#38BDF8"
            emissiveIntensity={2.5} // > 1.1 triggers selective bloom
            roughness={0.1}
          />
        </mesh>
      )}
    </group>
  );
}

// ============================================================================
// Scene Controller
// ============================================================================

function Scene() {
  const {
    positions3D,
    setNodePosition3D,
    activeAgentId,
    activeEdgeId,
    sandboxingAgentId,
    hitlPausedAgentId,
  } = useWorkspaceStore();

  const { status: swarmStatus } = useAgentStore();

  const controlsRef = useRef<any>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("researcher");

  // Disable orbit controls while dragging a node to prevent canvas rotation
  const handleDragStart = useCallback(() => {
    if (controlsRef.current) {
      controlsRef.current.enabled = false;
    }
  }, []);

  const handleDragEnd = useCallback(() => {
    if (controlsRef.current) {
      controlsRef.current.enabled = true;
    }
  }, []);

  // Compute node list with reactive status
  const nodes = useMemo(() => {
    return Object.keys(defaultNodeSpecs).map((id) => {
      const spec = defaultNodeSpecs[id];
      const pos = positions3D[id] || [0, 1.2, 0];

      let nodeStatus: AgentNodeStatus = "idle";
      if (activeAgentId === id || sandboxingAgentId === id) {
        nodeStatus = "running";
      } else if (
        hitlPausedAgentId === id ||
        (id === "human_approval" && hitlPausedAgentId !== null)
      ) {
        nodeStatus = "waiting";
      } else if (swarmStatus === "COMPLETED") {
        nodeStatus = "completed";
      }

      return {
        spec,
        position: pos,
        status: nodeStatus,
        isSelected: selectedNodeId === id,
      };
    });
  }, [
    positions3D,
    activeAgentId,
    sandboxingAgentId,
    hitlPausedAgentId,
    swarmStatus,
    selectedNodeId,
  ]);

  return (
    <>
      {/* 1. Realistic 3D Environment: Night HDRI, Specular Rim Lights, Reflector Floor & Coordinate Grid */}
      <SceneEnvironment gridSize={60} gridDivisions={60} />

      {/* 2. Interactive Orbit Camera Controls */}
      <OrbitControls
        ref={controlsRef}
        makeDefault
        enableDamping
        dampingFactor={0.06}
        maxPolarAngle={Math.PI / 2.08}
        minDistance={4}
        maxDistance={35}
      />

      {/* 3. 3D LangGraph Flow Edges */}
      {defaultEdges.map((edge) => {
        const startPos = positions3D[edge.source] || [0, 1.2, 0];
        const endPos = positions3D[edge.target] || [0, 1.2, 0];
        const isEdgeActive =
          activeEdgeId === edge.id ||
          activeAgentId === edge.source ||
          (edge.source === "researcher" && activeAgentId === "evaluator") ||
          (edge.source === "evaluator" && hitlPausedAgentId !== null);

        return (
          <Edge3D
            key={edge.id}
            id={edge.id}
            start={startPos}
            end={endPos}
            isActive={Boolean(isEdgeActive)}
          />
        );
      })}

      {/* 4. Interactive 3D Glass Monolith Agents & Tools */}
      {nodes.map(({ spec, position, status, isSelected }) => (
        <AgentNode3D
          key={spec.id}
          spec={spec}
          position={position}
          status={status}
          isSelected={isSelected}
          onSelect={(id) => setSelectedNodeId(id)}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onPositionChange={(id, newPos) => setNodePosition3D(id, newPos)}
        />
      ))}

      {/* 5. Optical Post-Processing: Selective Bloom for High-Emissive Cores & Pulses */}
      <PostProcessingEffects
        luminanceThreshold={1.1}
        luminanceSmoothing={0.3}
        intensity={0.8}
        multisampling={4}
      />
    </>
  );
}

// ============================================================================
// Main SSR-Safe SpatialCanvas3D Export
// ============================================================================

export interface SpatialCanvas3DProps {
  className?: string;
}

export default function SpatialCanvas3D({ className = "" }: SpatialCanvas3DProps) {
  return (
    <div
      className={`fixed inset-0 z-0 h-screen w-screen bg-[#030712] overflow-hidden ${className}`}
      data-testid="spatial-canvas-3d"
    >
      <Canvas
        shadows
        dpr={[1, 2]}
        camera={{ position: [0, 8, 14], fov: 45 }}
        gl={{
          antialias: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
        }}
      >
        <Scene />
      </Canvas>
    </div>
  );
}

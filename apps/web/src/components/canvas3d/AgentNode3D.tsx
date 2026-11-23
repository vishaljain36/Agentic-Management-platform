"use client";

import React, { useRef, useState, useMemo, useEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { RoundedBox, Html } from "@react-three/drei";
import * as THREE from "three";
import {
  useWorkspaceStore,
  Vector3Tuple,
} from "@/store/use-workspace-store";
import {
  Bot,
  Shield,
  Terminal,
  Database,
  Cpu,
  Sparkles,
  Zap,
} from "lucide-react";

export type AgentNodeStatus = "idle" | "running" | "waiting" | "completed" | "error";

export interface AgentSpec {
  id: string;
  label: string;
  role: string;
  model?: string;
  type?: "agent" | "tool" | "hitl";
  tools?: string[];
  category?: string;
}

export interface AgentNode3DProps {
  spec: AgentSpec;
  position: Vector3Tuple;
  status?: AgentNodeStatus;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  onPositionChange?: (id: string, newPosition: Vector3Tuple) => void;
}

export function AgentNode3D({
  spec,
  position,
  status = "idle",
  isSelected = false,
  onSelect,
  onDragStart,
  onDragEnd,
  onPositionChange,
}: AgentNode3DProps) {
  const monolithRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [localPos, setLocalPos] = useState<Vector3Tuple>(position);

  // Sync prop position when not dragging
  useEffect(() => {
    if (!isDragging) {
      setLocalPos(position);
    }
  }, [position, isDragging]);

  const { camera, raycaster, gl } = useThree();

  // Drag plane at the node's elevation on XZ
  const dragPlane = useMemo(
    () => new THREE.Plane(new THREE.Vector3(0, 1, 0), -position[1]),
    [position]
  );
  const planeIntersect = useMemo(() => new THREE.Vector3(), []);

  // Configure Core Color, Emissive Intensity, and Pulse Speed per Status
  const coreConfig = useMemo(() => {
    switch (status) {
      case "running":
        return {
          color: "#38BDF8", // Bright cyan
          emissiveIntensity: 2.4, // > 1.5 triggers selective bloom
          pulseSpeed: 4.2,
          pulseAmp: 0.8,
          statusLabel: "RUNNING / STREAMING",
          badgeColor: "text-[#38BDF8] border-[#38BDF8]/40 bg-[#38BDF8]/15 shadow-[0_0_15px_rgba(56,189,248,0.35)]",
        };
      case "waiting":
        return {
          color: "#F59E0B", // Amber HITL
          emissiveIntensity: 2.2,
          pulseSpeed: 6.0,
          pulseAmp: 0.9,
          statusLabel: "HITL PAUSED",
          badgeColor: "text-[#F59E0B] border-[#F59E0B]/40 bg-[#F59E0B]/15 shadow-[0_0_15px_rgba(245,158,11,0.35)]",
        };
      case "completed":
        return {
          color: "#10B981", // Emerald
          emissiveIntensity: 1.8,
          pulseSpeed: 1.6,
          pulseAmp: 0.3,
          statusLabel: "COMPLETED",
          badgeColor: "text-emerald-400 border-emerald-500/40 bg-emerald-500/15",
        };
      case "error":
        return {
          color: "#EF4444",
          emissiveIntensity: 2.5,
          pulseSpeed: 8.0,
          pulseAmp: 1.0,
          statusLabel: "ERROR",
          badgeColor: "text-red-400 border-red-500/40 bg-red-500/15",
        };
      case "idle":
      default:
        return {
          color: "#64748B", // Soft slate
          emissiveIntensity: 0.8,
          pulseSpeed: 1.2,
          pulseAmp: 0.2,
          statusLabel: "IDLE",
          badgeColor: "text-zinc-400 border-white/10 bg-white/5",
        };
    }
  }, [status]);

  // Core Animation Loop: Gentle bobbing, rotating octahedron, and pulsing emissive
  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();

    // Floating bob
    if (monolithRef.current) {
      const bob =
        status === "running"
          ? Math.sin(time * 3) * 0.08
          : Math.sin(time * 1.5 + localPos[0]) * 0.04;
      monolithRef.current.position.y = localPos[1] + bob;
    }

    // Octahedron Core rotation and emissive pulse
    if (coreRef.current) {
      coreRef.current.rotation.y += 0.015;
      coreRef.current.rotation.x += 0.01;

      const mat = coreRef.current.material as THREE.MeshStandardMaterial;
      if (mat) {
        const pulse =
          coreConfig.emissiveIntensity +
          Math.sin(time * coreConfig.pulseSpeed) * coreConfig.pulseAmp;
        mat.emissiveIntensity = Math.max(0.2, pulse);
      }
    }

    // Ground projection ring rotation
    if (ringRef.current) {
      ringRef.current.rotation.z += status === "running" ? 0.02 : 0.005;
    }
  });

  // Pointer Drag Interaction Handlers
  const handlePointerDown = (e: any) => {
    e.stopPropagation();
    setIsDragging(true);
    onSelect?.(spec.id);
    onDragStart?.();
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  const handlePointerMove = (e: any) => {
    if (!isDragging) return;
    e.stopPropagation();

    raycaster.setFromCamera(
      new THREE.Vector2(
        (e.clientX / gl.domElement.clientWidth) * 2 - 1,
        -(e.clientY / gl.domElement.clientHeight) * 2 + 1
      ),
      camera
    );

    if (raycaster.ray.intersectPlane(dragPlane, planeIntersect)) {
      const updatedPos: Vector3Tuple = [
        Number(planeIntersect.x.toFixed(3)),
        position[1],
        Number(planeIntersect.z.toFixed(3)),
      ];
      setLocalPos(updatedPos);
    }
  };

  const handlePointerUp = (e: any) => {
    if (isDragging) {
      e.stopPropagation();
      setIsDragging(false);
      onDragEnd?.();
      (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);

      // Persist final 3D coordinates into Zustand store
      onPositionChange?.(spec.id, localPos);
    }
  };

  // Node Category Icon
  const IconComponent = useMemo(() => {
    if (spec.id === "tool_vector") return Database;
    if (spec.id === "tool_sandbox") return Terminal;
    if (spec.type === "hitl") return Shield;
    return Bot;
  }, [spec.id, spec.type]);

  return (
    <group position={[localPos[0], 0, localPos[2]]}>
      {/* 1. Ground Projection Shadow / Energy Ring on the floor */}
      <mesh
        ref={ringRef}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0.02, 0]}
      >
        <ringGeometry args={[0.75, 1.05, 32]} />
        <meshBasicMaterial
          color={coreConfig.color}
          transparent
          opacity={status === "running" || status === "waiting" ? 0.75 : isHovered ? 0.45 : 0.2}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 2. Floating 3D Monolith Group */}
      <group
        ref={monolithRef}
        position={[0, localPos[1], 0]}
        onPointerOver={(e) => {
          e.stopPropagation();
          setIsHovered(true);
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setIsHovered(false);
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        {/* Beveled 3D Glass Monolith using MeshPhysicalMaterial */}
        <RoundedBox
          args={[1.4, 2.0, 0.75]}
          radius={0.08}
          smoothness={4}
          castShadow
          receiveShadow
        >
          <meshPhysicalMaterial
            transmission={0.88}
            roughness={0.12}
            ior={1.5}
            thickness={0.6}
            color="#18181b"
            transparent
            opacity={0.96}
            reflectivity={0.9}
            clearcoat={0.8}
            clearcoatRoughness={0.1}
          />
        </RoundedBox>

        {/* Outer Edge Accent Highlight (shows selection & hover) */}
        {(isSelected || isHovered || status === "running" || status === "waiting") && (
          <RoundedBox
            args={[1.42, 2.02, 0.77]}
            radius={0.08}
            smoothness={4}
          >
            <meshBasicMaterial
              color={isSelected ? "#8B5CF6" : coreConfig.color}
              wireframe
              transparent
              opacity={isSelected ? 0.8 : isHovered ? 0.5 : 0.3}
            />
          </RoundedBox>
        )}

        {/* 3. Glowing Status Core Octahedron inside the Glass Monolith */}
        <mesh ref={coreRef} position={[0, 0, 0]}>
          <octahedronGeometry args={[0.32, 0]} />
          <meshStandardMaterial
            color={coreConfig.color}
            emissive={coreConfig.color}
            emissiveIntensity={coreConfig.emissiveIntensity}
            roughness={0.12}
            metalness={0.2}
          />
        </mesh>

        {/* 4. Crisp Floating Cyber-Glass Badge */}
        <Html
          position={[0, 1.5, 0]}
          center
          distanceFactor={12}
          className="pointer-events-none select-none"
        >
          <div
            className={`min-w-[160px] rounded-xl border p-2.5 text-center backdrop-blur-cyber transition-all ${
              status === "running" || status === "waiting"
                ? "border-[#38BDF8] bg-[#0B0F19]/95 shadow-[0_0_20px_rgba(56,189,248,0.35)] scale-105"
                : isSelected
                ? "border-[#8B5CF6] bg-[#0B0F19]/95 shadow-neon-violet scale-100"
                : isHovered
                ? "border-white/30 bg-[#0B0F19]/90 scale-100"
                : "border-white/10 bg-[#0B0F19]/85 scale-95"
            }`}
          >
            {/* Header: Icon + Title */}
            <div className="flex items-center justify-between gap-1.5 pb-1 border-b border-white/10">
              <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-white">
                <IconComponent className="h-3.5 w-3.5 text-[#8B5CF6]" />
                {spec.label}
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-[8px] font-mono uppercase tracking-wider border ${coreConfig.badgeColor}`}
              >
                {coreConfig.statusLabel}
              </span>
            </div>

            {/* Role / Description */}
            <div className="mt-1 text-[9px] text-zinc-300 font-sans truncate">
              {spec.role}
            </div>

            {/* Model Badge */}
            {spec.model && (
              <div className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[8px] font-mono text-zinc-300 border border-white/10">
                <Cpu className="h-2.5 w-2.5 text-[#38BDF8]" />
                {spec.model}
              </div>
            )}
          </div>
        </Html>
      </group>
    </group>
  );
}

export default AgentNode3D;


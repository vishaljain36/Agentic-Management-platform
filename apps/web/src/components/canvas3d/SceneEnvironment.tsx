"use client";

import React, { Suspense } from "react";
import { Environment, MeshReflectorMaterial } from "@react-three/drei";

class EnvironmentErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(err: any) {
    console.warn("HDR Environment fetch fallback to procedural lighting:", err?.message || err);
  }
  render() {
    if (this.state.hasError) {
      return null;
    }
    return this.props.children;
  }
}

export interface SceneEnvironmentProps {
  gridSize?: number;
  gridDivisions?: number;
}

export function SceneEnvironment({
  gridSize = 60,
  gridDivisions = 60,
}: SceneEnvironmentProps) {
  return (
    <>
      {/* 1. HDRI Studio Night Preset with Error Boundary and Suspense */}
      <EnvironmentErrorBoundary>
        <Suspense fallback={null}>
          <Environment preset="night" />
        </Suspense>
      </EnvironmentErrorBoundary>

      {/* 2. Rim Directional Lights for Specular Edge Reflections */}
      {/* Violet rim light (back-left) */}
      <directionalLight
        position={[-12, 10, -10]}
        intensity={1.8}
        color="#8B5CF6"
      />
      {/* Cyan rim light (back-right) */}
      <directionalLight
        position={[12, 10, -10]}
        intensity={1.8}
        color="#38BDF8"
      />

      {/* Subtle top fill lighting */}
      <ambientLight intensity={0.35} />
      <directionalLight
        position={[0, 16, 12]}
        intensity={0.9}
        color="#ffffff"
        castShadow
        shadow-mapSize={[1024, 1024]}
      />

      {/* 3. Obsidian Ground Plane with Real-Time Reflection */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[100, 100]} />
        <MeshReflectorMaterial
          blur={[300, 100]}
          resolution={1024}
          mixBlur={1}
          mixStrength={40}
          roughness={0.25}
          depthScale={1.2}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
          color="#09090b"
          metalness={0.8}
          mirror={0.75}
        />
      </mesh>

      {/* 4. Spatial Coordinate Grid slightly above reflector plane */}
      <gridHelper
        args={[gridSize, gridDivisions, "#8B5CF6", "#1e1b4b"]}
        position={[0, 0.01, 0]}
      />
    </>
  );
}

export default SceneEnvironment;

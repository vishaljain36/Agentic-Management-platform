import React, { memo } from "react";
import {
  BaseEdge,
  getBezierPath,
  type EdgeProps,
} from "@xyflow/react";

interface EdgePulseData extends Record<string, unknown> {
  active?: boolean;
  amber?: boolean;
}

const EdgePulseComponent: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetPosition,
    targetX,
    targetY,
  });

  const edgeData = data as EdgePulseData | undefined;
  const isAmber = edgeData?.amber;
  const strokeColor = isAmber ? "#F59E0B" : "#8B5CF6";
  const glowFilter = isAmber
    ? "drop-shadow(0 0 4px rgba(245, 158, 11, 0.6))"
    : "drop-shadow(0 0 4px rgba(139, 92, 246, 0.6))";

  return (
    <>
      {/* Background base line */}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: "rgba(255, 255, 255, 0.12)",
          strokeWidth: 2,
        }}
      />

      {/* Kinetic pulse overlay */}
      <path
        d={edgePath}
        fill="none"
        stroke={strokeColor}
        strokeWidth={2.5}
        strokeDasharray="6 14"
        style={{
          filter: glowFilter,
        }}
        className="animate-edge-flow"
      />
    </>
  );
};

export const EdgePulse = memo(EdgePulseComponent);


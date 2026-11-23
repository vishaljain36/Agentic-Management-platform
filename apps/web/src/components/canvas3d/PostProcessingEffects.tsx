"use client";

import React from "react";
import { EffectComposer, Bloom } from "@react-three/postprocessing";

export interface PostProcessingEffectsProps {
  luminanceThreshold?: number;
  luminanceSmoothing?: number;
  intensity?: number;
  multisampling?: number;
}

export function PostProcessingEffects({
  luminanceThreshold = 1.1,
  luminanceSmoothing = 0.3,
  intensity = 0.8,
  multisampling = 4,
}: PostProcessingEffectsProps) {
  return (
    <EffectComposer multisampling={multisampling}>
      <Bloom
        luminanceThreshold={luminanceThreshold}
        luminanceSmoothing={luminanceSmoothing}
        mipmapBlur
        intensity={intensity}
      />
    </EffectComposer>
  );
}

export default PostProcessingEffects;


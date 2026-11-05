import React from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: "violet" | "cyan" | "emerald" | "amber" | "none";
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className,
  glow = "none",
  ...props
}) => {
  const glowStyles = {
    violet: "border-[#8B5CF6]/30 shadow-neon-violet hover:border-[#8B5CF6]/60",
    cyan: "border-[#06B6D4]/30 shadow-neon-cyan hover:border-[#06B6D4]/60",
    emerald: "border-[#10B981]/30 shadow-[0_0_20px_-3px_rgba(16,185,129,0.35)] hover:border-[#10B981]/60",
    amber: "border-[#F59E0B]/40 shadow-neon-amber animate-pulse-glow hover:border-[#F59E0B]/70",
    none: "border-white/10 hover:border-white/20",
  }[glow];

  return (
    <div
      className={cn(
        "relative rounded-xl border bg-[#111827]/70 p-4 backdrop-blur-cyber transition-all duration-300",
        glowStyles,
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};


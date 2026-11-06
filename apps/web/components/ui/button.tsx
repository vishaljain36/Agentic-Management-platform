import React from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "amber";
  size?: "sm" | "md" | "lg";
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = "primary",
  size = "md",
  disabled,
  ...props
}) => {
  const base =
    "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]";

  const sizes = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-5 py-2.5 text-base",
  }[size];

  const variants = {
    primary:
      "bg-[#8B5CF6] text-white hover:bg-[#7C3AED] shadow-[0_0_15px_-2px_rgba(139,92,246,0.5)] border border-[#8B5CF6]/50",
    secondary:
      "bg-[#06B6D4]/10 text-[#06B6D4] hover:bg-[#06B6D4]/20 border border-[#06B6D4]/30 shadow-[0_0_12px_-3px_rgba(6,182,212,0.3)]",
    amber:
      "bg-[#F59E0B] text-black font-semibold hover:bg-[#D97706] shadow-neon-amber border border-[#F59E0B]",
    danger:
      "bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30",
    ghost:
      "text-zinc-300 hover:text-white hover:bg-white/5 border border-transparent",
  }[variant];

  return (
    <button
      className={cn(base, sizes, variants, className)}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};


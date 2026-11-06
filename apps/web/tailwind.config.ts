import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        void: "#030712",
        "cyber-obsidian": "#030712",
        "cyber-panel": "rgba(17, 24, 39, 0.75)",
        "cyber-border": "rgba(255, 255, 255, 0.08)",
        "neon-violet": {
          DEFAULT: "#8B5CF6",
          glow: "rgba(139, 92, 246, 0.4)",
        },
        "neon-cyan": {
          DEFAULT: "#06B6D4",
          glow: "rgba(6, 182, 212, 0.4)",
        },
        "neon-emerald": {
          DEFAULT: "#10B981",
          glow: "rgba(16, 185, 129, 0.4)",
        },
        "neon-amber": {
          DEFAULT: "#F59E0B",
          pulse: "rgba(245, 158, 11, 0.4)",
        },
      },
      boxShadow: {
        "neon-violet": "0 0 20px -3px rgba(139, 92, 246, 0.35)",
        "neon-cyan": "0 0 20px -3px rgba(6, 182, 212, 0.35)",
        "neon-amber": "0 0 25px -2px rgba(245, 158, 11, 0.45)",
        "glass": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      backdropBlur: {
        cyber: "16px",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1", filter: "drop-shadow(0 0 8px rgba(245, 158, 11, 0.8))" },
          "50%": { opacity: "0.6", filter: "drop-shadow(0 0 2px rgba(245, 158, 11, 0.2))" },
        },
        edgeFlow: {
          "0%": { strokeDashoffset: "24" },
          "100%": { strokeDashoffset: "0" },
        },
      },
      animation: {
        "pulse-glow": "pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "edge-flow": "edgeFlow 1.2s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;


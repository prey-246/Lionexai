import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          base: "var(--background-base)",
          root: "var(--background-root)",
          card: "var(--background-card)",
          panel: "var(--background-panel)",
          elevated: "var(--background-elevated)",
          secondary: "var(--background-secondary)",
          // legacy numbered aliases used across pages
          "panel-1": "var(--background-panel-1)",
          "panel-2": "var(--background-panel-2)",
        },
        primary: {
          gold: "var(--primary-gold)",
          "gold-bright": "var(--primary-gold-bright)",
          emerald: "var(--primary-emerald)",
          "emerald-bright": "var(--primary-emerald-bright)",
          teal: "var(--primary-teal)",
          blue: "var(--primary-blue)",
        },
        danger: "var(--danger)",
        success: "var(--success)",
        warning: "var(--warning)",
        info: "var(--info)",
        status: {
          success: "var(--status-success)",
          danger: "var(--status-danger)",
          warning: "var(--status-warning)",
          info: "var(--status-info)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        border: {
          subtle: "var(--border-subtle)",
          default: "var(--border-default)",
          strong: "var(--border-strong)",
          secondary: "var(--border-secondary)",
          primary: "var(--border-primary)",
        },
        system: {
          gBg: "var(--gBg)",
          gBd: "var(--gBd)",
          tBg: "var(--tBg)",
          tBd: "var(--tBd)",
          rBg: "var(--rBg)",
          rBd: "var(--rBd)",
          bBg: "var(--bBg)",
          bBd: "var(--bBd)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        serif: ["var(--font-serif)"],
        display: ["var(--font-display)"],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "var(--radius-sm)",
        lg: "var(--radius-lg)",
      },
      boxShadow: {
        glow: "var(--shadow)",
        "glow-gold": "var(--shadow-glow-gold)",
        "glow-teal": "var(--shadow-glow-teal)",
      },
      backgroundImage: {
        "grad-brand": "var(--grad-brand)",
        "grad-gold": "var(--grad-gold)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s ease both",
        shimmer: "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;

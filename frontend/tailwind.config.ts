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
          card: "var(--background-card)",
          panel: "var(--background-panel)",
        },
        primary: {
          gold: "var(--primary-gold)",
          emerald: "var(--primary-emerald)",
          blue: "var(--primary-blue)",
        },
        danger: "var(--danger)",
        success: "var(--success)",
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        border: {
          subtle: "var(--border-subtle)",
          default: "var(--border-default)",
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
        }
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        serif: ["var(--font-serif)"],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
      },
    },
  },
  plugins: [],
};
export default config;

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
          root: "var(--background-root)",
          panel: {
            1: "var(--background-panel-1)",
            2: "var(--background-panel-2)",
          },
        },
        primary: {
          gold: "var(--primary-gold)",
          "gold-light": "var(--primary-gold-light)",
          teal: "var(--primary-teal)",
          "teal-light": "var(--primary-teal-light)",
          blue: "var(--primary-blue)",
        },
        danger: "var(--danger)",
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        border: {
          primary: "var(--border-primary)",
          secondary: "var(--border-secondary)",
        },
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
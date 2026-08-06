import forms from "@tailwindcss/forms";
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        border: "rgb(var(--color-border) / <alpha-value>)",
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        foreground: "rgb(var(--color-foreground) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        panel: "rgb(var(--color-panel) / <alpha-value>)",
        "panel-muted": "rgb(var(--color-panel-muted) / <alpha-value>)",
        primary: "rgb(var(--color-primary) / <alpha-value>)",
        "primary-contrast": "rgb(var(--color-primary-contrast) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
        "graph-node": "rgb(var(--color-graph-node) / <alpha-value>)",
        "graph-edge": "rgb(var(--color-graph-edge) / <alpha-value>)",
        "chart-a": "rgb(var(--color-chart-a) / <alpha-value>)",
        "chart-b": "rgb(var(--color-chart-b) / <alpha-value>)",
        "chart-c": "rgb(var(--color-chart-c) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Plus Jakarta Sans", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "SF Mono", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04)",
        glow: "0 0 20px -5px rgb(var(--color-primary) / 0.15)",
        "glow-lg": "0 0 35px -5px rgb(var(--color-primary) / 0.25)",
      },
    },
  },
  plugins: [forms],
};

export default config;


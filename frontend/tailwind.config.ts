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
        sans: ["SF Pro Display", "Geist Sans", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["Geist Mono", "SF Mono", "JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [forms],
};

export default config;

"use client";

import React, { useId } from "react";
import { cn } from "@/lib/utils";

export interface GitVaneLoaderProps {
  /** Size preset or pixel dimension */
  size?: "sm" | "md" | "lg" | "xl" | number;
  /** Primary label text under the loader. Pass `false` or `null` to hide. Defaults to "Please Wait..." */
  text?: React.ReactNode | string | false | null;
  /** Optional secondary subtitle */
  subtext?: React.ReactNode | string;
  /** Additional container CSS classes */
  className?: string;
  /** Whether to render centered in a full-screen container */
  fullScreen?: boolean;
}

const sizeMap = {
  sm: { box: "size-12", svg: 48, text: "text-xs" },
  md: { box: "size-16", svg: 64, text: "text-xs" },
  lg: { box: "size-20", svg: 80, text: "text-sm" },
  xl: { box: "size-24", svg: 96, text: "text-sm" },
};

export function GitVaneLoader({
  size = "md",
  text = "Please Wait...",
  subtext,
  className,
  fullScreen = false,
}: GitVaneLoaderProps) {
  const uniqueId = useId().replace(/:/g, "");

  const sizeConfig =
    typeof size === "string" && size in sizeMap
      ? sizeMap[size as keyof typeof sizeMap]
      : {
          box: typeof size === "number" ? `w-[${size}px] h-[${size}px]` : "size-16",
          svg: typeof size === "number" ? size : 64,
          text: "text-xs",
        };

  // Mathematical generation of the 6 aperture shutter blades
  // Center (64, 64), Outer radius R=50, Inner radius r=26
  const cx = 64;
  const cy = 64;
  const R = 50;
  const r = 26;

  const blades = [];
  for (let k = 0; k < 6; k++) {
    const a0 = ((k * 60 - 30) * Math.PI) / 180;
    const aMid = ((k * 60 + 30) * Math.PI) / 180;

    const x0 = (cx + R * Math.cos(a0)).toFixed(2);
    const y0 = (cy + R * Math.sin(a0)).toFixed(2);
    const xMid = (cx + r * Math.cos(aMid)).toFixed(2);
    const yMid = (cy + r * Math.sin(aMid)).toFixed(2);

    blades.push({
      k,
      d: `M ${x0} ${y0} L ${xMid} ${yMid}`,
      isRightHalf: k >= 2 && k <= 4,
    });
  }

  const content = (
    <div
      role="status"
      aria-live="polite"
      aria-label={typeof text === "string" ? text : "Loading..."}
      className={cn(
        "flex flex-col items-center justify-center gap-3.5 select-none",
        fullScreen && "min-h-screen bg-canvas text-foreground",
        className
      )}
    >
      <div
        className={cn(
          "relative flex items-center justify-center",
          typeof size === "string" ? sizeConfig.box : undefined
        )}
        style={
          typeof size === "number"
            ? { width: `${size}px`, height: `${size}px` }
            : undefined
        }
      >
        {/* Soft Ambient Breathing Glow Aura */}
        <div
          className="absolute inset-[-20%] rounded-full bg-primary/25 blur-xl pointer-events-none"
          style={{
            animation: `gitvane-glow-pulse-${uniqueId} 3.5s ease-in-out infinite`,
          }}
        />

        {/* SVG Graphic with Animated Iris & Flowing Git Graph */}
        <svg
          viewBox="0 0 128 128"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="size-full overflow-visible drop-shadow-sm"
        >
          <defs>
            {/* Outer Iris Shimmer Gradient */}
            <linearGradient
              id={`vane-grad-${uniqueId}`}
              x1="0%"
              y1="0%"
              x2="100%"
              y2="100%"
            >
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.85" />
              <stop offset="40%" stopColor="currentColor" stopOpacity="0.4" />
              <stop
                offset="60%"
                stopColor="rgb(var(--color-primary))"
                stopOpacity="0.9"
              />
              <stop
                offset="100%"
                stopColor="rgb(var(--color-primary))"
                stopOpacity="1"
              />
            </linearGradient>

            {/* Git Branch Streaming Energy Gradient */}
            <linearGradient
              id={`stream-grad-${uniqueId}`}
              x1="0%"
              y1="100%"
              x2="100%"
              y2="0%"
            >
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="50%" stopColor="rgb(var(--color-primary))" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>

            {/* Soft Glow Filter */}
            <filter
              id={`node-glow-${uniqueId}`}
              x="-40%"
              y="-40%"
              width="180%"
              height="180%"
            >
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            {/* Inner Iris Boundary Clip */}
            <clipPath id={`inner-clip-${uniqueId}`}>
              <circle cx="64" cy="64" r="25.5" />
            </clipPath>

            <style>{`
              @keyframes gitvane-spin-${uniqueId} {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
              }
              @keyframes gitvane-glow-pulse-${uniqueId} {
                0%, 100% { transform: scale(0.94); opacity: 0.35; }
                50% { transform: scale(1.2); opacity: 0.8; }
              }
              @keyframes gitvane-stream-dash-${uniqueId} {
                0% { stroke-dashoffset: 32; }
                100% { stroke-dashoffset: 0; }
              }
              @keyframes gitvane-node1-ping-${uniqueId} {
                0%, 100% { transform: scale(1); filter: drop-shadow(0 0 2px rgb(var(--color-primary) / 0.5)); }
                50% { transform: scale(1.22); filter: drop-shadow(0 0 10px rgb(var(--color-primary))) drop-shadow(0 0 16px #38bdf8); }
              }
              @keyframes gitvane-node2-ping-${uniqueId} {
                0%, 100% { transform: scale(1); filter: drop-shadow(0 0 2px rgb(var(--color-primary) / 0.5)); }
                50% { transform: scale(1.22); filter: drop-shadow(0 0 10px rgb(var(--color-primary))) drop-shadow(0 0 16px #38bdf8); }
              }
              @keyframes gitvane-dot-fade-${uniqueId} {
                0%, 20% { opacity: 0.15; transform: translateY(0); }
                50% { opacity: 1; transform: translateY(-2px); }
                80%, 100% { opacity: 0.15; transform: translateY(0); }
              }
            `}</style>
          </defs>

          {/* 1. Rotating Outer Iris / Aperture Shutter */}
          <g
            style={{
              transformOrigin: "64px 64px",
              animation: `gitvane-spin-${uniqueId} 1.4s linear infinite`,
              willChange: "transform",
            }}
          >
            {/* Outer Rim Circle */}
            <circle
              cx="64"
              cy="64"
              r="50"
              stroke={`url(#vane-grad-${uniqueId})`}
              strokeWidth="2.8"
            />

            {/* 6 Geometric Shutter Blades */}
            {blades.map((b) => (
              <path
                key={b.k}
                d={b.d}
                stroke={
                  b.isRightHalf
                    ? "rgb(var(--color-primary))"
                    : "currentColor"
                }
                strokeOpacity={b.isRightHalf ? 0.95 : 0.45}
                strokeWidth="2.4"
                strokeLinecap="round"
              />
            ))}

            {/* Inner Aperture Ring */}
            <circle
              cx="64"
              cy="64"
              r="26"
              stroke={`url(#vane-grad-${uniqueId})`}
              strokeWidth="2.4"
              strokeDasharray="6 3"
              strokeOpacity="0.85"
            />
          </g>

          {/* 2. Inner Git Graph Structure (Commit Flow) */}
          <g clipPath={`url(#inner-clip-${uniqueId})`}>
            {/* Background Branch Track */}
            <path
              d="M 43 73 L 53 53 L 71 71 L 85 57"
              stroke="rgb(var(--color-primary))"
              strokeOpacity="0.25"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Animated Energy Flow Beam */}
            <path
              d="M 43 73 L 53 53 L 71 71 L 85 57"
              stroke={`url(#stream-grad-${uniqueId})`}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="6 10"
              filter={`url(#node-glow-${uniqueId})`}
              style={{
                animation: `gitvane-stream-dash-${uniqueId} 0.45s linear infinite`,
              }}
            />

            {/* Node 1 (Upper-Left Commit - nicely positioned with comfortable margin) */}
            <g
              style={{
                transformOrigin: "53px 53px",
                animation: `gitvane-node1-ping-${uniqueId} 1.6s ease-in-out infinite`,
              }}
            >
              <circle
                cx="53"
                cy="53"
                r="5.6"
                fill="rgb(var(--color-canvas))"
                stroke="rgb(var(--color-primary))"
                strokeWidth="2.6"
              />
              <circle
                cx="53"
                cy="53"
                r="2.2"
                fill="#38bdf8"
                className="animate-pulse"
              />
            </g>

            {/* Node 2 (Lower-Right Commit - nicely positioned with comfortable margin) */}
            <g
              style={{
                transformOrigin: "71px 71px",
                animation: `gitvane-node2-ping-${uniqueId} 1.6s ease-in-out 0.8s infinite`,
              }}
            >
              <circle
                cx="71"
                cy="71"
                r="5.6"
                fill="rgb(var(--color-canvas))"
                stroke="rgb(var(--color-primary))"
                strokeWidth="2.6"
              />
              <circle
                cx="71"
                cy="71"
                r="2.2"
                fill="#38bdf8"
                className="animate-pulse"
              />
            </g>
          </g>
        </svg>
      </div>

      {/* Label and Subtext */}
      {text !== false && text !== null && (
        <div className="flex flex-col items-center gap-1 text-center">
          <p
            className={cn(
              "font-medium text-foreground/80 tracking-wide inline-flex items-center gap-0.5",
              sizeConfig.text
            )}
          >
            {typeof text === "string" && text.endsWith("...") ? (
              <>
                <span>{text.slice(0, -3)}</span>
                <span className="inline-flex font-mono">
                  <span
                    style={{
                      animation: `gitvane-dot-fade-${uniqueId} 1.4s infinite 0.1s`,
                    }}
                  >
                    .
                  </span>
                  <span
                    style={{
                      animation: `gitvane-dot-fade-${uniqueId} 1.4s infinite 0.3s`,
                    }}
                  >
                    .
                  </span>
                  <span
                    style={{
                      animation: `gitvane-dot-fade-${uniqueId} 1.4s infinite 0.5s`,
                    }}
                  >
                    .
                  </span>
                </span>
              </>
            ) : (
              <span>{text}</span>
            )}
          </p>

          {subtext && (
            <p className="text-[11px] text-muted tracking-tight">{subtext}</p>
          )}
        </div>
      )}
    </div>
  );

  return content;
}

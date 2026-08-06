"use client";

import { useMemo, useState } from "react";
import { Grid3X3, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { GraphEdge, GraphNode } from "@/lib/api/types";

export function RiskMatrixView({
  nodes,
  edges,
  selectedNodeId,
  onSelectNode,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: number | null;
  onSelectNode: (id: number) => void;
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);

  const nodeStats = useMemo(() => {
    const map = new Map<number, { inDegree: number; outDegree: number; totalEdges: number }>();
    for (const n of nodes) {
      map.set(n.id, { inDegree: 0, outDegree: 0, totalEdges: 0 });
    }
    for (const e of edges) {
      const src = map.get(e.source_file_id);
      const tgt = map.get(e.target_file_id);
      if (src) src.outDegree += 1;
      if (tgt) tgt.inDegree += 1;
    }
    for (const stat of map.values()) {
      stat.totalEdges = stat.inDegree + stat.outDegree;
    }
    return map;
  }, [nodes, edges]);

  const maxLoc = useMemo(() => Math.max(10, ...nodes.map((n) => n.loc)), [nodes]);
  const maxEdges = useMemo(() => {
    let max = 1;
    for (const stat of nodeStats.values()) {
      if (stat.totalEdges > max) max = stat.totalEdges;
    }
    return Math.max(1, max);
  }, [nodeStats]);

  const activeNode = useMemo(
    () => nodes.find((n) => n.id === (hoveredNodeId ?? selectedNodeId)) ?? null,
    [hoveredNodeId, selectedNodeId, nodes],
  );

  const highRiskCount = useMemo(() => {
    const locThreshold = maxLoc * 0.4;
    const edgeThreshold = maxEdges * 0.4;
    return nodes.filter((n) => {
      const stat = nodeStats.get(n.id);
      return n.loc >= locThreshold && (stat?.totalEdges ?? 0) >= edgeThreshold;
    }).length;
  }, [nodes, maxLoc, maxEdges, nodeStats]);

  return (
    <div className="space-y-4 p-4 bg-panel rounded-lg border border-border min-h-[540px]">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Grid3X3 className="size-4 text-primary" />
            Risk & Impact Matrix View
          </h3>
          <p className="text-xs text-muted mt-0.5">
            2D architectural quadrant mapping code size (LOC) against module coupling (edges).
          </p>
        </div>
        <div className="flex items-center gap-2">
          {highRiskCount > 0 && (
            <Badge tone="warning" className="flex items-center gap-1">
              <ShieldAlert className="size-3" />
              {highRiskCount} High Impact Modules
            </Badge>
          )}
          <Badge>{nodes.length} nodes</Badge>
        </div>
      </div>

      <div className="relative h-[440px] w-full rounded-lg border border-border bg-panel-muted/40 p-4 overflow-hidden select-none">
        {/* Quadrant background guides */}
        <div className="absolute inset-0 grid grid-cols-2 grid-rows-2">
          {/* Top-Left: High Coupling Hubs */}
          <div className="border-r border-b border-border/40 bg-warning/5 p-3">
            <span className="text-[11px] font-semibold text-warning tracking-wide uppercase">
              High Coupling Hubs (Low LOC / High Edges)
            </span>
          </div>
          {/* Top-Right: High Impact / High Complexity */}
          <div className="border-b border-border/40 bg-danger/5 p-3 text-right">
            <span className="text-[11px] font-semibold text-danger tracking-wide uppercase">
              High Risk / Core Modules (High LOC / High Edges)
            </span>
          </div>
          {/* Bottom-Left: Low Complexity Utilities */}
          <div className="border-r border-border/40 bg-success/5 p-3 flex items-end">
            <span className="text-[11px] font-semibold text-success tracking-wide uppercase">
              Low Complexity Utilities
            </span>
          </div>
          {/* Bottom-Right: Bulky Modules */}
          <div className="bg-muted/5 p-3 flex items-end justify-end">
            <span className="text-[11px] font-semibold text-muted tracking-wide uppercase">
              Bulky Standalone Logic
            </span>
          </div>
        </div>

        {/* Matrix Scatter Plot Area */}
        <svg className="absolute inset-0 size-full overflow-visible">
          {/* Axis Labels */}
          <line x1="5%" y1="92%" x2="95%" y2="92%" stroke="rgb(var(--color-border))" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="8%" y1="5%" x2="8%" y2="95%" stroke="rgb(var(--color-border))" strokeWidth="1" strokeDasharray="4 4" />

          {nodes.map((node) => {
            const stat = nodeStats.get(node.id) || { inDegree: 0, outDegree: 0, totalEdges: 0 };
            const cx = 12 + (Math.min(node.loc, maxLoc) / maxLoc) * 76;
            const cy = 85 - (Math.min(stat.totalEdges, maxEdges) / maxEdges) * 70;

            const isSelected = selectedNodeId === node.id;
            const isHovered = hoveredNodeId === node.id;

            return (
              <g
                key={node.id}
                className="cursor-pointer transition-transform duration-200"
                onClick={() => onSelectNode(node.id)}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId(null)}
              >
                <circle
                  cx={`${cx}%`}
                  cy={`${cy}%`}
                  r={isSelected || isHovered ? 9 : node.is_test ? 6 : 7}
                  className={`transition-all ${
                    isSelected
                      ? "fill-primary stroke-foreground stroke-2 shadow-lg"
                      : node.is_test
                      ? "fill-success stroke-panel stroke-2 hover:r-8"
                      : "fill-primary/80 stroke-panel stroke-2 hover:r-8 hover:fill-primary"
                  }`}
                />
                {(isSelected || isHovered) && (
                  <circle
                    cx={`${cx}%`}
                    cy={`${cy}%`}
                    r={14}
                    fill="none"
                    stroke="rgb(var(--color-primary))"
                    strokeWidth="1.5"
                    strokeDasharray="2 2"
                    className="animate-spin-slow"
                  />
                )}
              </g>
            );
          })}
        </svg>

        {/* Hover/Select Overlay Bar */}
        {activeNode && (
          <div className="absolute bottom-3 left-3 right-3 rounded-md border border-border bg-panel/95 p-2.5 backdrop-blur shadow-md flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2 truncate">
              <span className="font-semibold text-primary">{activeNode.path}</span>
              {activeNode.is_test && <Badge tone="success">Test</Badge>}
            </div>
            <div className="flex items-center gap-3 shrink-0 text-muted">
              <span>LOC: {activeNode.loc}</span>
              <span>Edges: {nodeStats.get(activeNode.id)?.totalEdges ?? 0}</span>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div className="rounded-md border border-border bg-panel-muted p-2.5">
          <span className="text-[10px] font-semibold text-muted uppercase">Max Lines of Code</span>
          <p className="mt-1 font-mono text-sm font-bold">{maxLoc} LOC</p>
        </div>
        <div className="rounded-md border border-border bg-panel-muted p-2.5">
          <span className="text-[10px] font-semibold text-muted uppercase">Max Module Coupling</span>
          <p className="mt-1 font-mono text-sm font-bold">{maxEdges} edges</p>
        </div>
        <div className="rounded-md border border-border bg-panel-muted p-2.5">
          <span className="text-[10px] font-semibold text-muted uppercase">High Risk Modules</span>
          <p className="mt-1 font-mono text-sm font-bold text-warning">{highRiskCount} files</p>
        </div>
        <div className="rounded-md border border-border bg-panel-muted p-2.5">
          <span className="text-[10px] font-semibold text-muted uppercase">Test Coverage Files</span>
          <p className="mt-1 font-mono text-sm font-bold text-success">
            {nodes.filter((n) => n.is_test).length} files
          </p>
        </div>
      </div>
    </div>
  );
}

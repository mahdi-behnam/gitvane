"use client";

import { useMemo } from "react";
import { Box, Code2, Database, Layers, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { GraphEdge, GraphNode } from "@/lib/api/types";

type LayerTier = {
  id: string;
  title: string;
  description: string;
  icon: typeof Layers;
  tone: "info" | "warning" | "success" | "neutral";
  nodes: GraphNode[];
};

export function HierarchyLayerView({
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
  const nodeEdgeCounts = useMemo(() => {
    const counts: Record<number, { in: number; out: number }> = {};
    for (const node of nodes) {
      counts[node.id] = { in: 0, out: 0 };
    }
    for (const edge of edges) {
      if (counts[edge.source_file_id]) counts[edge.source_file_id].out += 1;
      if (counts[edge.target_file_id]) counts[edge.target_file_id].in += 1;
    }
    return counts;
  }, [nodes, edges]);

  const layers: LayerTier[] = useMemo(() => {
    const apiLayer: GraphNode[] = [];
    const serviceLayer: GraphNode[] = [];
    const dataLayer: GraphNode[] = [];
    const testLayer: GraphNode[] = [];
    const otherLayer: GraphNode[] = [];

    for (const node of nodes) {
      const path = node.path.toLowerCase();
      if (node.is_test || path.includes("test")) {
        testLayer.push(node);
      } else if (
        path.includes("/api/") ||
        path.includes("/endpoints/") ||
        path.includes("/controllers/") ||
        path.includes("/views/") ||
        path.includes("/pages/") ||
        path.includes("/components/")
      ) {
        apiLayer.push(node);
      } else if (
        path.includes("/services/") ||
        path.includes("/domain/") ||
        path.includes("/usecases/") ||
        path.includes("/hooks/") ||
        path.includes("/store/") ||
        path.includes("/core/")
      ) {
        serviceLayer.push(node);
      } else if (
        path.includes("/models/") ||
        path.includes("/schemas/") ||
        path.includes("/db/") ||
        path.includes("/lib/") ||
        path.includes("/utils/") ||
        path.includes("/common/")
      ) {
        dataLayer.push(node);
      } else {
        otherLayer.push(node);
      }
    }

    return [
      {
        id: "api",
        title: "Presentation & API Layer",
        description: "HTTP endpoints, UI components, pages, and entry controllers.",
        icon: Code2,
        tone: "info",
        nodes: apiLayer,
      },
      {
        id: "service",
        title: "Domain & Core Business Services",
        description: "Business domain logic, orchestration services, and state managers.",
        icon: Layers,
        tone: "warning",
        nodes: serviceLayer,
      },
      {
        id: "data",
        title: "Data Access, Utilities & Models",
        description: "Database schemas, API clients, shared utility functions, and models.",
        icon: Database,
        tone: "neutral",
        nodes: dataLayer,
      },
      {
        id: "test",
        title: "Test & Quality Assurance Suite",
        description: "Unit, integration, and end-to-end verification specifications.",
        icon: ShieldCheck,
        tone: "success",
        nodes: testLayer,
      },
      ...(otherLayer.length > 0
        ? [
            {
              id: "other",
              title: "General Modules & Configuration",
              description: "Configuration files and general application modules.",
              icon: Box,
              tone: "neutral" as const,
              nodes: otherLayer,
            },
          ]
        : []),
    ];
  }, [nodes]);

  return (
    <div className="space-y-4 p-4 bg-panel rounded-lg border border-border min-h-[540px] max-h-[620px] overflow-y-auto">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Layers className="size-4 text-primary" />
            Architecture Layer Hierarchy View
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Categorized multi-tier architectural breakdown of repository dependencies.
          </p>
        </div>
        <Badge>{nodes.length} total nodes</Badge>
      </div>

      <div className="space-y-4">
        {layers.map((layer) => {
          const Icon = layer.icon;
          if (layer.nodes.length === 0) return null;

          return (
            <div
              key={layer.id}
              className="rounded-lg border border-border bg-panel-muted/40 p-3.5 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-panel border border-border">
                    <Icon className="size-4 text-primary" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-foreground flex items-center gap-2">
                      {layer.title}
                    </h4>
                    <p className="text-[11px] text-muted">{layer.description}</p>
                  </div>
                </div>
                <Badge tone={layer.tone}>{layer.nodes.length} files</Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2 pt-1">
                {layer.nodes.map((node) => {
                  const isSelected = selectedNodeId === node.id;
                  const edgeCount = nodeEdgeCounts[node.id] || { in: 0, out: 0 };

                  return (
                    <div
                      key={node.id}
                      onClick={() => onSelectNode(node.id)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && onSelectNode(node.id)}
                      className={`p-2.5 rounded-md border text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "border-primary bg-panel shadow-sm ring-1 ring-primary"
                          : "border-border/60 bg-panel hover:border-border hover:shadow-xs"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="font-mono text-xs font-semibold truncate break-all text-foreground">
                          {node.path}
                        </div>
                        {node.is_test && <Badge tone="success" className="text-[9px] py-0">Test</Badge>}
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-muted">
                        <span>{node.language || "unknown"} · {node.loc} LOC</span>
                        <div className="flex items-center gap-1">
                          <span className="rounded bg-panel-muted px-1.5 py-0.5 text-[10px]">
                            ?{edgeCount.in}
                          </span>
                          <span className="rounded bg-panel-muted px-1.5 py-0.5 text-[10px]">
                            ?{edgeCount.out}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

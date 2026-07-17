"use client";

import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { skipToken } from "@reduxjs/toolkit/query";
import { Filter, GitGraph, RefreshCw, Search } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { GraphEdge, GraphNode } from "@/lib/api/types";
import {
  useGetFileNeighborsQuery,
  useGetRepositoryQuery,
  useGetRepositorySubgraphQuery,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

type GraphFilters = {
  includeTests: boolean;
  language: string;
  maxNodes: number;
  search: string;
};

const defaultFilters: GraphFilters = {
  includeTests: true,
  language: "",
  maxNodes: 200,
  search: "",
};

export function GraphExplorerPage({ repositoryId }: { repositoryId: number }) {
  const validRepositoryId = Number.isFinite(repositoryId) ? repositoryId : null;
  const [draftFilters, setDraftFilters] = useState(defaultFilters);
  const [appliedFilters, setAppliedFilters] = useState(defaultFilters);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const subgraph = useGetRepositorySubgraphQuery(
    validRepositoryId
      ? {
          include_tests: appliedFilters.includeTests,
          language: appliedFilters.language.trim() || null,
          max_nodes: appliedFilters.maxNodes,
          repositoryId: validRepositoryId,
        }
      : skipToken,
  );
  const selectedGraphNode = useMemo(
    () => subgraph.data?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [selectedNodeId, subgraph.data?.nodes],
  );
  const neighbors = useGetFileNeighborsQuery(
    validRepositoryId && selectedNodeId
      ? { fileId: selectedNodeId, repositoryId: validRepositoryId }
      : skipToken,
  );
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  useEffect(() => {
    if (
      selectedNodeId &&
      subgraph.data &&
      !subgraph.data.nodes.some((node) => node.id === selectedNodeId)
    ) {
      setSelectedNodeId(null);
    }
  }, [selectedNodeId, subgraph.data]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedFilters({
      includeTests: draftFilters.includeTests,
      language: draftFilters.language.trim(),
      maxNodes: Math.max(1, draftFilters.maxNodes),
      search: draftFilters.search.trim(),
    });
  };

  const filteredNodes = useMemo(
    () => filterGraphNodes(subgraph.data?.nodes ?? [], appliedFilters.search),
    [appliedFilters.search, subgraph.data?.nodes],
  );
  const filteredNodeIds = useMemo(
    () => new Set(filteredNodes.map((node) => node.id)),
    [filteredNodes],
  );
  const filteredEdges = useMemo(
    () =>
      (subgraph.data?.edges ?? []).filter(
        (edge) =>
          filteredNodeIds.has(edge.source_file_id) &&
          filteredNodeIds.has(edge.target_file_id),
      ),
    [filteredNodeIds, subgraph.data?.edges],
  );
  const flowNodes = useMemo(
    () => buildFlowNodes(filteredNodes, selectedNodeId),
    [filteredNodes, selectedNodeId],
  );
  const flowEdges = useMemo(() => buildFlowEdges(filteredEdges), [filteredEdges]);
  const error = subgraph.error ? normalizeApiError(subgraph.error).message : null;
  const largeGraph =
    Boolean(subgraph.data?.nodes.length) &&
    subgraph.data!.nodes.length >= appliedFilters.maxNodes;

  if (!validRepositoryId) {
    return (
      <EmptyState
        description="The repository identifier in the route is not valid."
        title="Repository not found"
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="info">Graph</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Dependency graph</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Inspect repository files as dependency nodes, filter the visible subgraph,
            and select a file to review neighbors.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <h2 className="text-sm font-semibold">Graph controls</h2>
            <Badge>
              {subgraph.data
                ? `${subgraph.data.nodes.length} nodes`
                : "Repository subgraph"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 xl:grid-cols-[140px_1fr_1fr_auto_auto]"
            onSubmit={handleSubmit}
          >
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="graph-max-nodes">
                Max nodes
              </label>
              <Input
                id="graph-max-nodes"
                max={1000}
                min={1}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    maxNodes: Number(event.target.value),
                  }))
                }
                type="number"
                value={draftFilters.maxNodes}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="graph-language">
                Language filter
              </label>
              <Input
                id="graph-language"
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    language: event.target.value,
                  }))
                }
                placeholder="python"
                value={draftFilters.language}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="graph-search">
                Node search
              </label>
              <Input
                id="graph-search"
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    search: event.target.value,
                  }))
                }
                placeholder="indexing_service"
                value={draftFilters.search}
              />
            </div>
            <label className="flex h-9 items-center gap-2 self-end rounded-md border border-border bg-panel px-3 text-sm">
              <input
                checked={draftFilters.includeTests}
                className="size-4 rounded border-border text-primary focus:ring-primary"
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    includeTests: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Include tests
            </label>
            <div className="flex gap-2 self-end">
              <Button disabled={subgraph.isFetching} type="submit" variant="primary">
                <Filter aria-hidden="true" className="size-4" />
                Apply
              </Button>
              <Button
                disabled={subgraph.isFetching}
                onClick={() => subgraph.refetch()}
                type="button"
              >
                <RefreshCw aria-hidden="true" className="size-4" />
                Refresh
              </Button>
            </div>
          </form>

          {error ? (
            <Notice className="mt-4" tone="danger">
              {error}
            </Notice>
          ) : null}
          {largeGraph ? (
            <Notice className="mt-4" tone="warning">
              Current node limit reached. Narrow the graph with filters
              or increase the limit if you need more context.
            </Notice>
          ) : null}
        </CardContent>
      </Card>

      {subgraph.isLoading ? (
        <GraphLoadingState />
      ) : subgraph.isSuccess && subgraph.data.nodes.length === 0 ? (
        <EmptyState
          description="No graph nodes found for these filters."
          icon={<GitGraph aria-hidden="true" className="size-5" />}
          title="No graph nodes"
        />
      ) : flowNodes.length === 0 ? (
        <EmptyState
          description="No nodes match the current search. Try a broader path or symbol fragment."
          icon={<Search aria-hidden="true" className="size-5" />}
          title="No matching nodes"
        />
      ) : (
        <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
          <Card className="overflow-hidden">
            <div className="h-[620px] min-h-[480px] bg-panel-muted">
              <ReactFlow
                edges={flowEdges}
                fitView
                fitViewOptions={{ padding: 0.24 }}
                nodes={flowNodes}
                nodesDraggable
                onNodeClick={(_event, node) => setSelectedNodeId(Number(node.id))}
              >
                <Background color="rgb(var(--color-border))" gap={24} />
                <MiniMap
                  className="border-l border-t border-border bg-panel"
                  maskColor="rgb(var(--color-panel) / 0.72)"
                  nodeBorderRadius={8}
                  nodeColor={(node) =>
                    node.data?.isTest
                      ? "rgb(var(--color-success))"
                      : "rgb(var(--color-primary))"
                  }
                  nodeStrokeColor="rgb(var(--color-border))"
                  pannable
                  zoomable
                />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>
          </Card>
          <NodeDetailPanel
            neighbors={neighbors.data}
            neighborsError={
              neighbors.error ? normalizeApiError(neighbors.error).message : null
            }
            neighborsLoading={neighbors.isFetching}
            node={selectedGraphNode}
          />
        </section>
      )}
    </div>
  );
}

function filterGraphNodes(nodes: GraphNode[], search: string) {
  const query = search.trim().toLowerCase();

  if (!query) {
    return nodes;
  }

  return nodes.filter(
    (node) =>
      node.path.toLowerCase().includes(query) ||
      node.language.toLowerCase().includes(query),
  );
}

function buildFlowNodes(nodes: GraphNode[], selectedNodeId: number | null): Node[] {
  const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));

  return nodes.map((node, index) => {
    const row = Math.floor(index / columns);
    const column = index % columns;
    const selected = selectedNodeId === node.id;

    return {
      data: {
        isTest: node.is_test,
        label: node.path,
      },
      id: String(node.id),
      position: {
        x: column * 260,
        y: row * 150,
      },
      sourcePosition: Position.Right,
      style: {
        background: node.is_test
          ? "rgb(var(--color-success) / 0.08)"
          : "rgb(var(--color-graph-node) / 0.32)",
        border: "1px solid rgb(var(--color-border))",
        borderRadius: 8,
        boxShadow: selected ? "0 0 0 2px rgb(var(--color-primary) / 0.22)" : "none",
        color: "rgb(var(--color-foreground))",
        fontFamily: "Geist Mono, SF Mono, monospace",
        fontSize: 11,
        lineHeight: 1.45,
        minHeight: 60,
        padding: 10,
        width: 220,
      },
      targetPosition: Position.Left,
    };
  });
}

function buildFlowEdges(edges: GraphEdge[]): Edge[] {
  return edges.map((edge) => ({
    animated: edge.confidence >= 0.75,
    data: {
      confidence: edge.confidence,
    },
    id: String(edge.id),
    label: edge.edge_type,
    labelBgPadding: [8, 4],
    labelBgStyle: {
      fill: "rgb(var(--color-panel))",
      fillOpacity: 0.92,
    },
    labelStyle: {
      fill: "rgb(var(--color-muted))",
      fontSize: 10,
      fontWeight: 600,
    },
    markerEnd: {
      color: "rgb(var(--color-graph-edge))",
      type: MarkerType.ArrowClosed,
    },
    source: String(edge.source_file_id),
    style: {
      stroke: "rgb(var(--color-graph-edge))",
      strokeWidth: Math.max(1, edge.confidence * 2),
    },
    target: String(edge.target_file_id),
    type: "smoothstep",
  }));
}

function GraphLoadingState() {
  return (
    <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <Card className="p-5">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="mt-5 h-[520px] w-full" />
      </Card>
      <Card className="p-5">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-5 h-24 w-full" />
        <Skeleton className="mt-4 h-36 w-full" />
      </Card>
    </section>
  );
}

function NodeDetailPanel({
  neighbors,
  neighborsError,
  neighborsLoading,
  node,
}: {
  neighbors?: { edges: GraphEdge[]; nodes: GraphNode[] };
  neighborsError: string | null;
  neighborsLoading: boolean;
  node: GraphNode | null;
}) {
  if (!node) {
    return (
      <EmptyState
        description="Select a graph node to inspect file metadata and neighboring dependencies."
        icon={<GitGraph aria-hidden="true" className="size-5" />}
        title="No node selected"
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2">
          <Badge tone={node.is_test ? "success" : "info"}>
            {node.is_test ? "Test file" : "Source file"}
          </Badge>
          <h2 className="break-all font-mono text-sm font-semibold">{node.path}</h2>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <Metric label="Language" value={node.language || "unknown"} />
          <Metric label="LOC" value={String(node.loc)} />
          <Metric label="Generated" value={node.is_generated ? "Yes" : "No"} />
          <Metric label="File ID" value={String(node.id)} />
        </dl>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold">File neighbors</h3>
            <Badge>{neighbors?.nodes.length ?? 0} nodes</Badge>
          </div>
          {neighborsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          ) : neighborsError ? (
            <Notice tone="danger">{neighborsError}</Notice>
          ) : neighbors && neighbors.nodes.length > 0 ? (
            <div className="space-y-2">
              {neighbors.nodes.slice(0, 8).map((neighbor) => (
                <div
                  className="rounded-md border border-border bg-panel-muted px-3 py-2"
                  key={neighbor.id}
                >
                  <p className="break-all font-mono text-xs font-semibold">
                    {neighbor.path}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {neighbor.language || "unknown"} · {neighbor.loc} LOC
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">No neighboring files returned.</p>
          )}
        </div>

        {neighbors && neighbors.edges.length > 0 ? (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Neighbor edges</h3>
            {neighbors.edges.slice(0, 8).map((edge) => (
              <div
                className="rounded-md border border-border px-3 py-2 text-xs"
                key={edge.id}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono">{edge.edge_type}</span>
                  <span className="font-mono text-muted">
                    {edge.confidence.toFixed(2)}
                  </span>
                </div>
                <p className="mt-1 break-all text-muted">
                  {edge.source_path} → {edge.target_path}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {label}
      </dt>
      <dd className="mt-1 break-all font-mono text-xs font-semibold">{value}</dd>
    </div>
  );
}

"use client";

import { useState, useMemo } from "react";
import { FileCode, Folder, FolderOpen, Sparkles, TestTube2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { GraphEdge, GraphNode } from "@/lib/api/types";

type TreeNode = {
  name: string;
  fullPath: string;
  isDirectory: boolean;
  graphNode?: GraphNode;
  children: TreeNode[];
};

export function DependencyTreeView({
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
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});

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

  const treeRoot = useMemo(() => {
    const root: TreeNode = { name: "root", fullPath: "", isDirectory: true, children: [] };

    for (const node of nodes) {
      const parts = node.path.split("/");
      let current = root;
      let currentPath = "";

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        const isLast = i === parts.length - 1;

        let existing = current.children.find((c) => c.name === part);
        if (!existing) {
          existing = {
            name: part,
            fullPath: currentPath,
            isDirectory: !isLast,
            graphNode: isLast ? node : undefined,
            children: [],
          };
          current.children.push(existing);
        }
        current = existing;
      }
    }

    const sortTree = (item: TreeNode) => {
      item.children.sort((a, b) => {
        if (a.isDirectory !== b.isDirectory) return a.isDirectory ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      item.children.forEach(sortTree);
    };
    sortTree(root);

    return root;
  }, [nodes]);

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [path]: prev[path] === undefined ? false : !prev[path],
    }));
  };

  const renderTreeItem = (item: TreeNode, depth: number = 0) => {
    if (item.isDirectory) {
      const isExpanded = expandedFolders[item.fullPath] !== false;
      return (
        <div key={item.fullPath || item.name} className="space-y-1">
          {item.name !== "root" && (
            <button
              onClick={() => toggleFolder(item.fullPath)}
              type="button"
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-semibold text-muted hover:bg-panel-muted transition-colors"
              style={{ paddingLeft: `${depth * 14 + 8}px` }}
            >
              {isExpanded ? (
                <FolderOpen className="size-4 shrink-0 text-primary" />
              ) : (
                <Folder className="size-4 shrink-0 text-muted" />
              )}
              <span className="font-mono text-foreground">{item.name}</span>
              <span className="ml-auto text-[10px] text-muted font-normal">
                {item.children.length} items
              </span>
            </button>
          )}
          {(isExpanded || item.name === "root") && (
            <div className="space-y-1 border-l border-border/40 ml-3 pl-1">
              {item.children.map((child) => renderTreeItem(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    const gNode = item.graphNode!;
    const isSelected = selectedNodeId === gNode.id;
    const edgeCount = nodeEdgeCounts[gNode.id] || { in: 0, out: 0 };

    return (
      <div
        key={gNode.id}
        onClick={() => onSelectNode(gNode.id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && onSelectNode(gNode.id)}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        className={`group flex flex-wrap items-center justify-between gap-2 rounded-md px-2.5 py-2 text-xs transition-all cursor-pointer border ${
          isSelected
            ? "border-primary bg-primary/10 shadow-sm font-medium"
            : "border-transparent hover:border-border hover:bg-panel-muted"
        }`}
      >
        <div className="flex items-center gap-2 min-w-0 overflow-hidden">
          {gNode.is_test ? (
            <TestTube2 className="size-4 shrink-0 text-success" />
          ) : (
            <FileCode className="size-4 shrink-0 text-primary" />
          )}
          <span className="font-mono truncate text-foreground">{item.name}</span>
          {gNode.is_test && (
            <Badge tone="success" className="text-[10px] py-0 px-1.5">
              Test
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 font-mono text-[11px] text-muted">
          <span>{gNode.language || "unknown"}</span>
          <span>·</span>
          <span>{gNode.loc} LOC</span>
          <div className="flex items-center gap-1 pl-1">
            <span className="rounded bg-panel-muted px-1.5 py-0.5 text-[10px]" title="Incoming dependencies">
              ?{edgeCount.in}
            </span>
            <span className="rounded bg-panel-muted px-1.5 py-0.5 text-[10px]" title="Outgoing dependencies">
              ?{edgeCount.out}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-3 p-4 bg-panel rounded-lg border border-border min-h-[540px] max-h-[620px] overflow-y-auto">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            Hierarchical Module Directory Tree
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Browse file dependencies in a structured folder tree with depth & coupling metrics.
          </p>
        </div>
        <Badge>{nodes.length} files</Badge>
      </div>

      <div className="space-y-1 pt-1">
        {treeRoot.children.map((child) => renderTreeItem(child, 0))}
      </div>
    </div>
  );
}

"use client";

import { Clock, Cpu, FileCode, Loader2, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Notice } from "@/components/ui/notice";
import type { IndexingProgressEvent } from "@/lib/api/types";
import type { ConnectionState } from "@/lib/hooks/useIndexingSSE";

interface IndexingProgressCardProps {
  connectionState: ConnectionState;
  progress: IndexingProgressEvent | null;
}

export function IndexingProgressCard({
  connectionState,
  progress,
}: IndexingProgressCardProps) {
  if (!progress) {
    return (
      <Card className="border-info/30 bg-info/5">
        <CardContent className="flex items-center gap-3 py-6">
          <Loader2 className="size-5 animate-spin text-info" />
          <p className="text-sm text-muted">Initializing repository indexer...</p>
        </CardContent>
      </Card>
    );
  }

  const pct = Math.min(100, Math.max(0, progress.progress_percentage || 0));

  const formatETA = (seconds: number | null | undefined) => {
    if (seconds === null || seconds === undefined) {
      return "Calculating...";
    }
    if (seconds <= 0) {
      return "Wrapping up...";
    }
    if (seconds < 60) {
      return `~${seconds}s remaining`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `~${mins}m ${secs}s remaining`;
  };

  return (
    <Card className="border-info/40 bg-card shadow-sm transition-all">
      <CardHeader className="flex flex-col gap-2 pb-2 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2.5">
          <Badge tone="info" className="flex items-center gap-1.5 px-2.5 py-1 text-xs">
            <Loader2 className="size-3.5 animate-spin" />
            Indexing Active
          </Badge>
          <span className="text-sm font-medium">{progress.phase_name}</span>
        </div>

        <div className="flex items-center gap-2">
          {connectionState === "connected" ? (
            <Badge tone="success" className="flex items-center gap-1 text-xs">
              <Wifi className="size-3" />
              Live
            </Badge>
          ) : connectionState === "reconnecting" ? (
            <Badge tone="warning" className="flex items-center gap-1 text-xs">
              <Loader2 className="size-3 animate-spin" />
              Reconnecting...
            </Badge>
          ) : connectionState === "error" ? (
            <Badge tone="danger" className="flex items-center gap-1 text-xs">
              <WifiOff className="size-3" />
              Disconnected
            </Badge>
          ) : null}

          <span className="font-mono text-sm font-semibold text-foreground">
            {pct.toFixed(1)}%
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2">
        {/* Progress Bar */}
        <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Multi-Phase Metric Cards */}
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 p-3">
            <div className="rounded-md bg-primary/10 p-2 text-primary">
              <FileCode className="size-4" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted">Parsed Files</p>
              <p className="font-mono text-sm font-semibold">
                {progress.files_processed} / {progress.files_total || 0}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 p-3">
            <div className="rounded-md bg-info/10 p-2 text-info">
              <Cpu className="size-4" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted">Chunks Embedded</p>
              <p className="font-mono text-sm font-semibold">
                {progress.chunks_processed} / {progress.chunks_total || 0}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 p-3">
            <div className="rounded-md bg-success/10 p-2 text-success">
              <Clock className="size-4" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted">Estimated ETA</p>
              <p className="font-mono text-sm font-semibold">
                {formatETA(progress.estimated_seconds_remaining)}
              </p>
            </div>
          </div>
        </div>

        {progress.error ? (
          <Notice tone="danger" className="mt-2">
            Indexing encountered an error: {progress.error}
          </Notice>
        ) : null}
      </CardContent>
    </Card>
  );
}

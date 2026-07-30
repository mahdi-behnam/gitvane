"use client";

import { AlertCircle, Loader2, Play, RefreshCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { AddRepositoryDialog } from "@/components/repositories/add-repository-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/table";
import { normalizeApiError } from "@/lib/api/errors";
import type { IndexingProgressEvent, Repository } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { useIndexingSSE } from "@/lib/hooks/useIndexingSSE";
import {
  useDeleteRepositoryMutation,
  useIndexRepositoryMutation,
  useListRepositoriesQuery,
} from "@/store/api/repolensApi";
import { useAppSelector } from "@/store/hooks";

function RepositorySkeletonRows() {
  return (
    <>
      <TableRow>
        <TableCell className="text-muted" colSpan={5}>
          Loading repositories
        </TableCell>
      </TableRow>
      {Array.from({ length: 3 }, (_, index) => (
        <TableRow key={index}>
          <TableCell>
            <Skeleton className="h-4 w-32" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-20" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-24" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-36" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-8 w-16" />
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

function RepositoryStatusCell({
  repository,
  isLocallyIndexing = false,
  onComplete,
}: {
  isLocallyIndexing?: boolean;
  onComplete: () => void;
  repository: Repository;
}) {
  const token = useAppSelector((state) => state.auth.accessToken);
  const isIndexing = repository.status === "indexing" || isLocallyIndexing;

  const initialProgress = (repository.repo_metadata?.indexing_progress as
    | IndexingProgressEvent
    | undefined) ?? null;

  const { progress } = useIndexingSSE({
    enabled: isIndexing,
    initialProgress,
    onComplete,
    repositoryId: repository.id,
    token,
  });

  if (isIndexing) {
    const pct = progress?.progress_percentage ?? 0;
    const eta = progress?.estimated_seconds_remaining;

    const etaText =
      eta === null || eta === undefined
        ? "Calculating..."
        : eta <= 0
        ? "Wrapping up..."
        : `~${eta}s left`;

    return (
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Badge tone="info" className="flex items-center gap-1 text-xs">
            <Loader2 className="size-3 animate-spin" />
            Indexing ({pct.toFixed(0)}%)
          </Badge>
          <span className="font-mono text-xs text-muted">{etaText}</span>
        </div>
        <div className="h-1.5 w-28 overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <Badge tone={repository.status === "indexed" ? "success" : "neutral"}>
      {repository.status}
    </Badge>
  );
}

export function RepositoryManagementPage() {
  const repositories = useListRepositoriesQuery();
  const [activeIndexingIds, setActiveIndexingIds] = useState<Record<number, boolean>>({});

  const apiError = repositories.error
    ? normalizeApiError(repositories.error).message
    : null;

  const handleIndexingStarted = (repositoryId: string) => {
    setActiveIndexingIds((prev) => ({ ...prev, [repositoryId]: true }));
  };

  const handleIndexingEnded = (repositoryId: string) => {
    setActiveIndexingIds((prev) => ({ ...prev, [repositoryId]: false }));
    void repositories.refetch();
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="info">Repositories</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Repositories</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Register repositories, inspect indexing state, and choose where analysis
            work should begin.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={repositories.isFetching}
            onClick={() => void repositories.refetch()}
            type="button"
          >
            <RefreshCw aria-hidden="true" className="size-4" />
            Refresh
          </Button>
          <AddRepositoryDialog />
        </div>
      </div>

      {apiError ? (
        <EmptyState
          action={
            <Button onClick={() => void repositories.refetch()} type="button">
              <RefreshCw aria-hidden="true" className="size-4" />
              Try again
            </Button>
          }
          description={apiError}
          icon={<AlertCircle aria-hidden="true" className="size-5" />}
          title="Repositories could not be loaded"
        />
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Repository inventory</h2>
              <Badge>{repositories.data?.total ?? 0} total</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Name</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell>Branch</TableHeaderCell>
                  <TableHeaderCell>Last indexed</TableHeaderCell>
                  <TableHeaderCell>Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {repositories.isLoading ? <RepositorySkeletonRows /> : null}
                {!repositories.isLoading && repositories.data?.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <EmptyState
                        className="m-4 border-0 bg-panel-muted"
                        description="Add a repository with a clone URL to start indexing code."
                        title="No repository records"
                      />
                    </TableCell>
                  </TableRow>
                ) : null}
                {repositories.data?.items.map((repository) => (
                  <TableRow key={repository.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{repository.name}</p>
                        <p className="mt-1 max-w-md truncate font-mono text-xs text-muted">
                          {repository.clone_url ?? "No source"}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <RepositoryStatusCell
                        isLocallyIndexing={Boolean(activeIndexingIds[repository.id])}
                        onComplete={() => handleIndexingEnded(repository.id)}
                        repository={repository}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted">
                      {repository.default_branch ?? repository.current_ref ?? "Unknown"}
                    </TableCell>
                    <TableCell className="text-muted">
                      {formatDateTime(repository.indexed_at)}
                    </TableCell>
                    <TableCell>
                      <RepositoryRowActions
                        isLocallyIndexing={Boolean(activeIndexingIds[repository.id])}
                        onIndexFailed={() => handleIndexingEnded(repository.id)}
                        onIndexStarted={() => handleIndexingStarted(repository.id)}
                        repository={repository}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RepositoryRowActions({
  isLocallyIndexing = false,
  onIndexFailed,
  onIndexStarted,
  repository,
}: {
  isLocallyIndexing?: boolean;
  onIndexFailed: () => void;
  onIndexStarted: () => void;
  repository: Repository;
}) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [indexRepository, indexState] = useIndexRepositoryMutation();
  const [deleteRepository, deleteState] = useDeleteRepositoryMutation();

  const isIndexingActive =
    repository.status === "indexing" || isLocallyIndexing || indexState.isLoading;

  const indexError = indexState.error
    ? normalizeApiError(indexState.error).message
    : null;
  const deleteError = deleteState.error
    ? normalizeApiError(deleteState.error).message
    : null;

  const handleIndex = async () => {
    onIndexStarted();
    try {
      await indexRepository({
        body: {},
        repositoryId: repository.id,
      }).unwrap();
    } catch {
      onIndexFailed();
    }
  };

  const handleDelete = async () => {
    try {
      await deleteRepository(repository.id).unwrap();
      setDeleteOpen(false);
    } catch {
      // The rendered mutation state below carries the normalized API message.
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      <Button asChild size="sm">
        <Link href={`/repositories/${repository.id}`}>View</Link>
      </Button>
      <Button
        disabled={isIndexingActive}
        onClick={handleIndex}
        size="sm"
        type="button"
      >
        <Play aria-hidden="true" className="size-3.5" />
        {isIndexingActive ? "Indexing" : "Index"}
      </Button>
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogTrigger asChild>
          <Button size="sm" type="button" variant="danger">
            <Trash2 aria-hidden="true" className="size-3.5" />
            Delete
          </Button>
        </DialogTrigger>
        <DialogContent title="Delete repository">
          <div className="space-y-4">
            <p className="text-sm leading-6 text-muted">
              Delete {repository.name} from RepoLens and ask the backend to remove its
              local clone.
            </p>
            {deleteError ? <Notice tone="danger">{deleteError}</Notice> : null}
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => setDeleteOpen(false)}
                type="button"
                variant="ghost"
              >
                Cancel
              </Button>
              <Button
                disabled={deleteState.isLoading}
                onClick={handleDelete}
                type="button"
                variant="danger"
              >
                Delete repository
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {indexError ? <p className="w-full text-xs text-danger">{indexError}</p> : null}
    </div>
  );
}

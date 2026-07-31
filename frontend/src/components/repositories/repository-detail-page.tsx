"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import {
  AlertCircle,
  BarChart3,
  FlaskConical,
  GitGraph,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useId, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DeleteRepoModal } from "@/components/repositories/delete-repo-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import { formatDateTime } from "@/lib/format";
import {
  useDeleteRepositoryMutation,
  useGetIndexStatusQuery,
  useGetRepositoryQuery,
  useIndexRepositoryMutation,
} from "@/store/api/repolensApi";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";
import { useIndexingSSE } from "@/lib/hooks/useIndexingSSE";
import { IndexingProgressCard } from "./indexing-progress-card";

const toolLinks = [
  { icon: Search, label: "Search", suffix: "search" },
  { icon: Play, label: "Impact", suffix: "impact" },
  { icon: GitGraph, label: "Graph", suffix: "graph" },
  { icon: ShieldAlert, label: "Risk", suffix: "risk" },
  { icon: FlaskConical, label: "Tests", suffix: "tests" },
  { icon: BarChart3, label: "Evaluation", suffix: "evaluation" },
];

export function RepositoryDetailPage({ repositoryId }: { repositoryId: string }) {
  const validRepositoryId = typeof repositoryId === "string" && repositoryId.trim() !== "" ? repositoryId : null;
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const indexStatus = useGetIndexStatusQuery(validRepositoryId ?? skipToken);
  const [indexRepository, indexState] = useIndexRepositoryMutation();
  const [deleteRepository, deleteState] = useDeleteRepositoryMutation();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [ref, setRef] = useState("");
  const dispatch = useAppDispatch();
  const router = useRouter();
  const formId = useId();

  const token = useAppSelector((state) => state.auth.accessToken);

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  const handleRefresh = useCallback(() => {
    void repository.refetch();
    void indexStatus.refetch();
  }, [repository, indexStatus]);

  const isIndexing =
    repository.data?.status === "indexing" ||
    indexStatus.data?.status === "indexing" ||
    indexState.isLoading ||
    indexState.data?.status === "indexing";

  const { connectionState, progress } = useIndexingSSE({
    repositoryId: validRepositoryId,
    enabled: isIndexing,
    token,
    initialProgress: indexStatus.data?.progress,
    onComplete: () => {
      indexState.reset();
      handleRefresh();
    },
  });

  const handleIndex = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validRepositoryId) {
      return;
    }

    await indexRepository({
      body: {
        ref: ref.trim() || null,
      },
      repositoryId: validRepositoryId,
    });
  };

  const handleDelete = async () => {
    if (!validRepositoryId) {
      return;
    }

    try {
      await deleteRepository(validRepositoryId).unwrap();
      setDeleteOpen(false);
      router.push("/repositories");
    } catch {
      // The rendered mutation state below carries the normalized API message.
    }
  };

  const error = repository.error ? normalizeApiError(repository.error).message : null;
  const deleteError = deleteState.error
    ? normalizeApiError(deleteState.error).message
    : null;
  const indexError = indexState.error
    ? normalizeApiError(indexState.error).message
    : null;

  if (!validRepositoryId) {
    return (
      <EmptyState
        description="The repository identifier in the route is not valid."
        title="Repository not found"
      />
    );
  }

  if (repository.isLoading) {
    return (
      <div className="mx-auto max-w-7xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-36 w-full" />
        <Skeleton className="h-52 w-full" />
      </div>
    );
  }

  if (error || !repository.data) {
    return (
      <EmptyState
        action={
          <Button onClick={() => void repository.refetch()} type="button">
            <RefreshCw aria-hidden="true" className="size-4" />
            Try again
          </Button>
        }
        description={error ?? "The repository could not be found."}
        icon={<AlertCircle aria-hidden="true" className="size-5" />}
        title="Repository could not be loaded"
      />
    );
  }

  const repositoryData = repository.data;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="info">Repository</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            {repositoryData.name}
          </h1>
          <p className="mt-3 max-w-3xl truncate font-mono text-sm text-muted">
            {repositoryData.clone_url ?? "No source"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleRefresh} type="button">
            <RefreshCw aria-hidden="true" className="size-4" />
            Refresh
          </Button>
          <Button onClick={() => setDeleteOpen(true)} variant="danger">
            <Trash2 aria-hidden="true" className="size-4" />
            Delete
          </Button>
          <DeleteRepoModal
            error={deleteError}
            isLoading={deleteState.isLoading}
            onConfirm={handleDelete}
            onOpenChange={setDeleteOpen}
            open={deleteOpen}
            repositoryName={repositoryData.name}
          />
        </div>
      </div>

      {isIndexing || progress?.status === "indexing" ? (
        <IndexingProgressCard
          connectionState={connectionState}
          progress={progress ?? indexStatus.data?.progress ?? null}
        />
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Repository identity</h2>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4 text-sm">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Status</dt>
                <dd>
                  <Badge
                    tone={repositoryData.status === "indexed" ? "success" : "neutral"}
                  >
                    {repositoryData.status}
                  </Badge>
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Default branch</dt>
                <dd className="font-mono text-xs">
                  {repositoryData.default_branch ?? "Unknown"}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Current ref</dt>
                <dd className="font-mono text-xs">
                  {repositoryData.current_ref ?? "Unknown"}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Last indexed commit</dt>
                <dd className="font-mono text-xs">
                  {repositoryData.last_indexed_commit ?? "None"}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-muted">Indexed at</dt>
                <dd className="text-right text-muted">
                  {formatDateTime(repositoryData.indexed_at)}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Index status</h2>
          </CardHeader>
          <CardContent>
            {indexStatus.isLoading ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }, (_, index) => (
                  <Skeleton className="h-16" key={index} />
                ))}
              </div>
            ) : indexStatus.error ? (
              <p className="text-sm text-danger">
                {normalizeApiError(indexStatus.error).message}
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Files" value={indexStatus.data?.file_count ?? 0} />
                <Metric label="Symbols" value={indexStatus.data?.symbol_count ?? 0} />
                <Metric label="Chunks" value={indexStatus.data?.chunk_count ?? 0} />
                <Metric
                  label="Edges"
                  value={indexStatus.data?.dependency_edge_count ?? 0}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Index repository</h2>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 lg:grid-cols-[1fr_auto]"
            onSubmit={handleIndex}
          >
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor={`${formId}-ref`}>
                Ref
              </label>
              <Input
                id={`${formId}-ref`}
                onChange={(event) => setRef(event.target.value)}
                placeholder="branch, tag, or commit"
                value={ref}
              />
            </div>
            <div className="flex items-end">
              <Button disabled={indexState.isLoading} type="submit" variant="primary">
                <Play aria-hidden="true" className="size-4" />
                {indexState.isLoading ? "Indexing" : "Run index"}
              </Button>
            </div>
          </form>
          {indexError ? (
            <Notice className="mt-4" tone="danger">
              {indexError}
            </Notice>
          ) : null}
          {indexState.data && indexState.data.status !== "indexing" ? (
            <Notice className="mt-4" tone="success">
              Indexed {indexState.data.files_indexed} files and{" "}
              {indexState.data.symbols_indexed} symbols.
            </Notice>
          ) : null}
        </CardContent>
      </Card>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        {toolLinks.map((item) => {
          const Icon = item.icon;
          return (
            <Card className="transition hover:bg-panel-muted" key={item.suffix}>
              <Link
                className="block p-4"
                href={`/repositories/${repositoryData.id}/${item.suffix}`}
              >
                <Icon aria-hidden="true" className="size-4 text-primary" />
                <p className="mt-3 text-sm font-medium">{item.label}</p>
              </Link>
            </Card>
          );
        })}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-panel-muted p-4">
      <p className="font-mono text-xs uppercase tracking-[0.08em] text-muted">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold">{value.toLocaleString()}</p>
    </div>
  );
}

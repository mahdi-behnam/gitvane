"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { AlertCircle, FlaskConical, GitGraph, RefreshCw, Send, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useId, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Textarea } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type {
  ChangedFileInput,
  ImpactAnalyzeResponse,
  ImpactRunResponse,
  ImpactedFile,
} from "@/lib/api/types";
import {
  useGetRepositoryQuery,
  useLazyGetImpactRunQuery,
  useRunImpactAnalysisMutation,
} from "@/store/api/repolensApi";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";
import {
  setDependencyDepth,
  setIncludeChangedFilesInImpact,
  setIncludeExplanations,
} from "@/store/slices/appPreferencesSlice";

type InputMode = "changed_files" | "raw_diff" | "refs";

const inputModes: { label: string; value: InputMode }[] = [
  { label: "Changed files", value: "changed_files" },
  { label: "Raw diff", value: "raw_diff" },
  { label: "Refs", value: "refs" },
];

function parseChangedFiles(value: string): ChangedFileInput[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((path) => ({
      change_type: "modified",
      changed_lines: [],
      old_path: null,
      path,
    }));
}

export function ImpactAnalysisPage({
  initialPath,
  repositoryId,
}: {
  initialPath?: string;
  repositoryId: string;
}) {
  const validRepositoryId = typeof repositoryId === "string" && repositoryId.trim() !== "" ? repositoryId : null;
  const searchParams = useSearchParams();
  const pathParam = initialPath ?? searchParams?.get("path") ?? searchParams?.get("search") ?? searchParams?.get("query") ?? "";

  const formId = useId();
  const [mode, setMode] = useState<InputMode>("changed_files");
  const [changedFiles, setChangedFiles] = useState(
    pathParam || "backend/app/services/indexing_service.py",
  );
  const [rawDiff, setRawDiff] = useState("");
  const [baseRef, setBaseRef] = useState("");
  const [headRef, setHeadRef] = useState("");
  const [topK, setTopK] = useState(20);
  const preferences = useAppSelector((state) => state.appPreferences);
  const includeExplanation = preferences.includeExplanations;
  const includeChangedFiles = preferences.includeChangedFilesInImpact;
  const dependencyDepth = preferences.dependencyDepth;
  const [analysisRunId, setAnalysisRunId] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const [runImpactAnalysis, analysisState] = useRunImpactAnalysisMutation();
  const [lookupRun, lookupState] = useLazyGetImpactRunQuery();
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  useEffect(() => {
    if (pathParam) {
      setChangedFiles(pathParam);
      setMode("changed_files");
    }
  }, [pathParam]);

  const parsedChangedFiles = useMemo(
    () => parseChangedFiles(changedFiles),
    [changedFiles],
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validRepositoryId) {
      setClientError("The repository identifier in the route is not valid.");
      return;
    }

    if (mode === "changed_files" && parsedChangedFiles.length === 0) {
      setClientError("Enter at least one changed file path.");
      return;
    }

    if (mode === "raw_diff" && !rawDiff.trim()) {
      setClientError("Paste a raw diff before running analysis.");
      return;
    }

    if (mode === "refs" && (!baseRef.trim() || !headRef.trim())) {
      setClientError("Enter both base and head refs.");
      return;
    }

    setClientError(null);
    await runImpactAnalysis({
      base_ref: mode === "refs" ? baseRef.trim() : null,
      changed_files: mode === "changed_files" ? parsedChangedFiles : null,
      head_ref: mode === "refs" ? headRef.trim() : null,
      include_changed_files_in_predictions: includeChangedFiles,
      include_explanation: includeExplanation,
      max_dependency_depth: dependencyDepth,
      raw_diff: mode === "raw_diff" ? rawDiff : null,
      repository_id: validRepositoryId,
      top_k: topK,
    });
  };

  const handleLookup = async () => {
    const parsedRunId = Number(analysisRunId);
    if (!Number.isFinite(parsedRunId) || parsedRunId <= 0) {
      setClientError("Enter a valid analysis run ID.");
      return;
    }

    setClientError(null);
    await lookupRun(parsedRunId);
  };

  const apiError = analysisState.error
    ? normalizeApiError(analysisState.error).message
    : lookupState.error
      ? normalizeApiError(lookupState.error).message
      : null;
  const error = clientError ?? apiError;

  if (!validRepositoryId) {
    return (
      <EmptyState
        description="The repository identifier in the route is not valid."
        title="Repository not found"
      />
    );
  }

  if (repository.error) {
    return (
      <EmptyState
        action={
          <Button onClick={() => void repository.refetch()} type="button">
            <RefreshCw aria-hidden="true" className="size-4" />
            Try again
          </Button>
        }
        description={normalizeApiError(repository.error).message}
        icon={<AlertCircle aria-hidden="true" className="size-5" />}
        title="Repository not found"
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge tone="info">Impact</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Impact analysis</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
            Predict likely impacted files from changed paths, a raw diff, or a base/head
            comparison.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Inputs</h2>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <div className="inline-flex rounded-md border border-border bg-panel p-1">
                {inputModes.map((item) => (
                  <button
                    aria-pressed={mode === item.value}
                    className={
                      mode === item.value
                        ? "rounded bg-panel-muted px-3 py-1.5 text-sm text-foreground"
                        : "rounded px-3 py-1.5 text-sm text-muted hover:bg-panel-muted hover:text-foreground"
                    }
                    key={item.value}
                    onClick={() => setMode(item.value)}
                    type="button"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="mt-4">
                {mode === "changed_files" ? (
                  <>
                    <label
                      className="block text-sm font-medium"
                      htmlFor={`${formId}-changed-files`}
                    >
                      Changed files
                    </label>
                    <Textarea
                      id={`${formId}-changed-files`}
                      onChange={(event) => setChangedFiles(event.target.value)}
                      value={changedFiles}
                    />
                  </>
                ) : null}
                {mode === "raw_diff" ? (
                  <>
                    <label
                      className="block text-sm font-medium"
                      htmlFor={`${formId}-raw-diff`}
                    >
                      Raw diff
                    </label>
                    <Textarea
                      id={`${formId}-raw-diff`}
                      onChange={(event) => setRawDiff(event.target.value)}
                      placeholder="diff --git a/file.ts b/file.ts"
                      value={rawDiff}
                    />
                  </>
                ) : null}
                {mode === "refs" ? (
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <label
                        className="block text-sm font-medium"
                        htmlFor={`${formId}-base-ref`}
                      >
                        Base ref
                      </label>
                      <Input
                        id={`${formId}-base-ref`}
                        onChange={(event) => setBaseRef(event.target.value)}
                        placeholder="main"
                        value={baseRef}
                      />
                    </div>
                    <div className="space-y-2">
                      <label
                        className="block text-sm font-medium"
                        htmlFor={`${formId}-head-ref`}
                      >
                        Head ref
                      </label>
                      <Input
                        id={`${formId}-head-ref`}
                        onChange={(event) => setHeadRef(event.target.value)}
                        placeholder="development"
                        value={headRef}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label
                  className="block text-sm font-medium"
                  htmlFor={`${formId}-top-k`}
                >
                  Top results
                </label>
                <Input
                  id={`${formId}-top-k`}
                  max={100}
                  min={1}
                  onChange={(event) => setTopK(Number(event.target.value))}
                  type="number"
                  value={topK}
                />
              </div>
              <div className="space-y-2">
                <label
                  className="block text-sm font-medium"
                  htmlFor={`${formId}-depth`}
                >
                  Dependency depth
                </label>
                <Input
                  id={`${formId}-depth`}
                  max={5}
                  min={1}
                  onChange={(event) =>
                    dispatch(
                      setDependencyDepth(Math.max(1, Number(event.target.value))),
                    )
                  }
                  type="number"
                  value={dependencyDepth}
                />
              </div>
              <div className="space-y-3 pt-1">
                <label className="flex items-center gap-2 text-sm text-muted">
                  <input
                    checked={includeExplanation}
                    className="rounded border-border text-primary focus:ring-primary"
                    onChange={(event) =>
                      dispatch(setIncludeExplanations(event.target.checked))
                    }
                    type="checkbox"
                  />
                  Include explanation
                </label>
                <label className="flex items-center gap-2 text-sm text-muted">
                  <input
                    checked={includeChangedFiles}
                    className="rounded border-border text-primary focus:ring-primary"
                    onChange={(event) =>
                      dispatch(setIncludeChangedFilesInImpact(event.target.checked))
                    }
                    type="checkbox"
                  />
                  Include changed files in predictions
                </label>
              </div>
            </div>

            {error ? <Notice tone="danger">{error}</Notice> : null}

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={analysisState.isLoading}
                type="submit"
                variant="primary"
              >
                <Send aria-hidden="true" className="size-4" />
                {analysisState.isLoading ? "Analyzing" : "Analyze impact"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Run lookup</h2>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[220px_auto]">
            <Input
              aria-label="Analysis run ID"
              onChange={(event) => setAnalysisRunId(event.target.value)}
              placeholder="Analysis run ID"
              value={analysisRunId}
            />
            <Button
              disabled={lookupState.isFetching}
              onClick={handleLookup}
              type="button"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
              Refresh run
            </Button>
          </div>
        </CardContent>
      </Card>

      {analysisState.isLoading ? <ImpactLoadingState /> : null}
      {lookupState.data ? (
        <ImpactRunResults repositoryId={validRepositoryId} response={lookupState.data} />
      ) : analysisState.data ? (
        <ImpactResults repositoryId={validRepositoryId} response={analysisState.data} />
      ) : !analysisState.isLoading ? (
        <EmptyState
          description="Run analysis to inspect changed files, impacted files, evidence, tests, and risk."
          icon={<ShieldAlert aria-hidden="true" className="size-5" />}
          title="No analysis results"
        />
      ) : null}
    </div>
  );
}

function ImpactLoadingState() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }, (_, index) => (
        <Card className="p-5" key={index}>
          <Skeleton className="h-4 w-56" />
          <Skeleton className="mt-4 h-20 w-full" />
        </Card>
      ))}
    </div>
  );
}

function ImpactResults({
  repositoryId,
  response,
}: {
  repositoryId: string;
  response: ImpactAnalyzeResponse;
}) {
  return (
    <section className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Analysis result</h2>
            <Badge>Run {response.analysis_run_id}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="Changed files" value={response.changed_files.length} />
            <Metric label="Changed symbols" value={response.changed_symbols.length} />
            <Metric label="Impacted files" value={response.impacted_files.length} />
          </div>
        </CardContent>
      </Card>

      <ChangedFiles files={response.changed_files} />
      <ChangedSymbols symbols={response.changed_symbols} />
      <ImpactedFiles files={response.impacted_files} repositoryId={repositoryId} />
      <RecommendedTests tests={response.recommended_tests} />
      <RiskSummary files={response.risk_summary.highest_risk_files} repositoryId={repositoryId} />
      {response.llm_explanation ? (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Evidence summary</h2>
          </CardHeader>
          <CardContent>
            <Notice className="mb-3" tone="warning">
              LLM explanations summarize computed evidence and do not score predictions.
            </Notice>
            <p className="text-sm leading-6 text-muted">{response.llm_explanation}</p>
          </CardContent>
        </Card>
      ) : null}
    </section>
  );
}

function ImpactRunResults({
  repositoryId,
  response,
}: {
  repositoryId: string;
  response: ImpactRunResponse;
}) {
  return (
    <section className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Stored run</h2>
            <Badge>{response.status}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="Changed files" value={response.changed_files.length} />
            <Metric label="Changed symbols" value={response.changed_symbols.length} />
            <Metric label="Predictions" value={response.predictions.length} />
          </div>
        </CardContent>
      </Card>
      <ImpactedFiles files={response.predictions} repositoryId={repositoryId} />
    </section>
  );
}

function ChangedFiles({ files }: { files: ChangedFileInput[] }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">Changed files</h2>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {files.map((file) => (
            <div
              className="rounded-md border border-border bg-panel-muted px-3 py-2 font-mono text-xs"
              key={file.path}
            >
              {file.path}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ChangedSymbols({
  symbols,
}: {
  symbols: ImpactAnalyzeResponse["changed_symbols"];
}) {
  if (symbols.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">Changed symbols</h2>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {symbols.map((symbol) => (
            <div
              className="rounded-md border border-border bg-panel-muted px-3 py-2 text-sm"
              key={`${symbol.path}:${symbol.qualified_name}`}
            >
              <span className="font-medium">{symbol.qualified_name}</span>
              <span className="ml-2 font-mono text-xs text-muted">
                {symbol.path}:{symbol.start_line}-{symbol.end_line}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ImpactedFiles({
  files,
  repositoryId,
}: {
  files: ImpactedFile[];
  repositoryId: string;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Likely impacted files</h2>
        <Badge>{files.length} files</Badge>
      </div>
      {files.map((file) => (
        <Card key={file.path}>
          <CardHeader>
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <h3 className="truncate font-mono text-sm font-semibold">
                  #{file.rank} {file.path}
                </h3>
                <p className="mt-1 text-xs text-muted">Score {file.score.toFixed(3)}</p>
              </div>
              <Badge tone="info">{file.score.toFixed(3)}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-4">
              {Object.entries(file.component_scores).map(([name, score]) => (
                <Metric key={name} label={name} value={score} precision />
              ))}
            </div>
            <div className="mt-4 space-y-2">
              {file.reasons.map((reason) => (
                <div
                  className="rounded-md border border-border bg-panel-muted px-3 py-2 text-sm"
                  key={`${file.path}:${reason.type}:${reason.message}`}
                >
                  <span className="font-medium">{reason.type}</span>
                  <span className="ml-2 text-muted">{reason.message}</span>
                </div>
              ))}
            </div>
            {file.recommended_tests.length > 0 ? (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
                  Recommended tests
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {file.recommended_tests.map((test) => (
                    <Badge key={`${file.path}:${test.path}`} tone="success">
                      {test.path}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild size="sm" variant="ghost">
                <Link
                  href={`/repositories/${repositoryId}/graph?path=${encodeURIComponent(file.path)}`}
                >
                  <GitGraph aria-hidden="true" className="size-4" />
                  Open graph
                </Link>
              </Button>
              <Button asChild size="sm" variant="ghost">
                <Link
                  href={`/repositories/${repositoryId}/tests?path=${encodeURIComponent(file.path)}`}
                >
                  <FlaskConical aria-hidden="true" className="size-4" />
                  Recommend tests
                </Link>
              </Button>
              <Button asChild size="sm" variant="ghost">
                <Link
                  href={`/repositories/${repositoryId}/risk?path=${encodeURIComponent(file.path)}`}
                >
                  <ShieldAlert aria-hidden="true" className="size-4" />
                  View risk
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}

function RecommendedTests({
  tests,
}: {
  tests: ImpactAnalyzeResponse["recommended_tests"];
}) {
  if (tests.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">Recommended tests</h2>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {tests.map((test) => (
            <div
              className="rounded-md border border-border bg-panel-muted px-3 py-2 text-sm"
              key={test.path}
            >
              <span className="font-mono text-xs">{test.path}</span>
              <span className="ml-2 text-muted">
                {test.reason ?? "Evidence linked"}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function RiskSummary({
  files,
  repositoryId,
}: {
  files: Record<string, unknown>[];
  repositoryId: string;
}) {
  if (files.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">Risk summary</h2>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {files.map((file, index) => {
            const pathStr = String(file.path ?? file.file_path ?? "Unknown file");
            const rawScore = typeof file.risk_score === "number" ? file.risk_score : typeof file.score === "number" ? file.score : null;

            return (
              <div
                className="flex items-center justify-between rounded-md border border-warning/20 bg-warning/10 px-3 py-2 text-sm text-warning"
                key={index}
              >
                <div className="flex items-center gap-2 font-mono text-xs truncate max-w-lg">
                  <span className="truncate">{pathStr}</span>
                  {rawScore !== null ? (
                    <Badge tone="warning">
                      Risk {(rawScore * (rawScore <= 1 ? 100 : 1)).toFixed(0)}
                    </Badge>
                  ) : null}
                </div>
                <Button asChild className="h-7 text-xs" size="sm" variant="ghost">
                  <Link
                    href={`/repositories/${repositoryId}/risk?path=${encodeURIComponent(pathStr)}`}
                  >
                    <ShieldAlert aria-hidden="true" className="mr-1 size-3.5" />
                    View risk
                  </Link>
                </Button>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({
  label,
  precision,
  value,
}: {
  label: string;
  precision?: boolean;
  value: number;
}) {
  return (
    <div className="rounded-lg border border-border bg-panel-muted p-4">
      <p className="font-mono text-xs uppercase tracking-[0.08em] text-muted">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold">
        {precision ? value.toFixed(2) : value.toLocaleString()}
      </p>
    </div>
  );
}

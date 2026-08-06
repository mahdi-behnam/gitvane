"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { AlertCircle, BarChart3, Play, RefreshCw, Search } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Label,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TermTooltip } from "@/components/ui/term-tooltip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { Selector, SelectorOption } from "@/components/ui/selector";
import { normalizeApiError } from "@/lib/api/errors";
import type { EvaluationMethod, EvaluationStatusResponse } from "@/lib/api/types";
import { formatPercent, formatSnakeCase } from "@/lib/format";
import {
  useGetEvaluationReportMarkdownQuery,
  useGetEvaluationStatusQuery,
  useGetRepositoryQuery,
  useListEvaluationRunsQuery,
  useRunEvaluationMutation,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

const evaluationMethods: EvaluationMethod[] = [
  "hybrid",
  "dependency_only",
  "semantic_only",
  "cochange_only",
];

const METHOD_DESCRIPTIONS: Record<string, string> = {
  hybrid:
    "Combines structural dependency graph, semantic text embeddings, and historical git co-changes into a weighted ensemble score.",
  dependency_only:
    "Evaluates downstream impact purely based on AST module imports and dependency graph traversal.",
  semantic_only:
    "Evaluates code relevance purely using natural language vector embeddings and semantic similarity.",
  cochange_only:
    "Evaluates impact purely based on historical git commit co-modification frequency.",
  method: "Analysis technique or algorithm variant tested in this evaluation run.",
  methods:
    "Collection of analysis techniques and algorithm variants evaluated in this benchmark run.",
};

function parseKValues(value: string) {
  return value
    .split(",")
    .map((part) => Number(part.trim()))
    .filter((value) => Number.isFinite(value) && value > 0);
}

export function EvaluationDashboardPage({ repositoryId }: { repositoryId: string }) {
  const validRepositoryId =
    typeof repositoryId === "string" && repositoryId.trim() !== ""
      ? repositoryId
      : null;
  const [name, setName] = useState("Benchmark run");
  const [commitLimit, setCommitLimit] = useState(50);
  const [kValues, setKValues] = useState("5,10,20");
  const [methods, setMethods] = useState<EvaluationMethod[]>(["hybrid"]);
  const [lookupRunId, setLookupRunId] = useState("");
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const evaluationRunsQuery = useListEvaluationRunsQuery(
    validRepositoryId ?? skipToken,
  );
  const [runEvaluation, runState] = useRunEvaluationMutation();
  const status = useGetEvaluationStatusQuery(activeRunId ?? skipToken);
  const report = useGetEvaluationReportMarkdownQuery(activeRunId ?? skipToken);
  const dispatch = useAppDispatch();

  const evaluationRunOptions: SelectorOption[] = useMemo(() => {
    const runs = evaluationRunsQuery.data ?? [];
    return runs.map((run) => ({
      badge: run.status,
      description: `Commit limit: ${run.commit_limit} • Methods: ${(run.methods ?? []).join(", ")} • ${run.created_at ? new Date(run.created_at).toLocaleString() : ""}`,
      label: `${run.name} (#${run.evaluation_run_id})`,
      value: String(run.evaluation_run_id),
    }));
  }, [evaluationRunsQuery.data]);

  const methodSelectorOptions: SelectorOption[] = useMemo(
    () =>
      evaluationMethods.map((m) => ({
        description: METHOD_DESCRIPTIONS[m],
        label: formatSnakeCase(m),
        value: m,
      })),
    [],
  );

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  const handleRun = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validRepositoryId) {
      setClientError("The repository identifier in the route is not valid.");
      return;
    }

    if (!name.trim()) {
      setClientError("Evaluation run name cannot be empty.");
      return;
    }

    const parsedKValues = parseKValues(kValues);
    if (parsedKValues.length === 0) {
      setClientError("Enter at least one positive integer for K values.");
      return;
    }

    if (methods.length === 0) {
      setClientError("Select at least one evaluation method.");
      return;
    }

    setClientError(null);
    try {
      const response = await runEvaluation({
        commit_limit: commitLimit,
        k_values: parsedKValues,
        methods,
        name: name.trim(),
        repository_id: validRepositoryId,
      }).unwrap();

      setActiveRunId(response.evaluation_run_id);
    } catch (err: unknown) {
      console.error("Failed to run evaluation:", err);
    }
  };

  const handleLookup = () => {
    const runId = Number(lookupRunId.trim());
    if (!Number.isInteger(runId) || runId <= 0) {
      setClientError("Enter a valid numeric evaluation run ID.");
      return;
    }

    setClientError(null);
    setActiveRunId(runId);
  };

  const apiError = runState.error ? normalizeApiError(runState.error).message : null;
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
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            Evaluation dashboard
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
            Benchmark code search accuracy, retrieval metrics, and impact prediction
            precision against ground-truth repository tasks.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Run evaluation</h2>
          <p className="mt-1 text-xs text-muted">
            Configure and launch a benchmark evaluation run across historical commits.
          </p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleRun}>
            <div className="grid gap-4 lg:grid-cols-[1fr_160px_180px]">
              <div className="space-y-2">
                <label className="block text-sm font-medium" htmlFor="evaluation-name">
                  Name
                </label>
                <Input
                  id="evaluation-name"
                  onChange={(event) => setName(event.target.value)}
                  placeholder="e.g. Benchmark run 1"
                  value={name}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  <label htmlFor="evaluation-commit-limit">Commit limit</label>
                  <TermTooltip description="Maximum number of historical git commits evaluated during this benchmark run." />
                </div>
                <Input
                  id="evaluation-commit-limit"
                  min={1}
                  onChange={(event) => setCommitLimit(Number(event.target.value))}
                  type="number"
                  value={commitLimit}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  <label htmlFor="evaluation-k-values">K values</label>
                  <TermTooltip description="Comma-separated rank cutoffs (e.g. 5, 10, 20) used to calculate Recall@K and Precision@K." />
                </div>
                <Input
                  id="evaluation-k-values"
                  onChange={(event) => setKValues(event.target.value)}
                  value={kValues}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-sm font-medium">
                <span id="evaluation-methods-label">Methods</span>
                <TermTooltip description="Analysis algorithms and model variants tested during this evaluation run." />
              </div>
              <Selector
                id="evaluation-methods"
                mode="multi"

                onChange={(val) =>
                  setMethods(Array.isArray(val) ? (val as EvaluationMethod[]) : [])
                }
                options={methodSelectorOptions}
                placeholder="Select evaluation methods..."
                searchable={false}
                value={methods}
              />
            </div>

            <div className="flex flex-col gap-3 border-t border-border pt-4 md:flex-row md:items-center md:justify-between">
              <p className="text-xs leading-5 text-muted">
                Evaluation quality depends on repository history and available ground
                truth. Treat metrics as directional, not definitive.
              </p>
              <Button disabled={runState.isLoading} type="submit" variant="primary">
                <Play aria-hidden="true" className="size-4" />
                {runState.isLoading ? "Starting" : "Run evaluation"}
              </Button>
            </div>
          </form>

          {error ? (
            <Notice className="mt-4" tone="danger">
              {error}
            </Notice>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Lookup evaluation run</h2>
          <p className="mt-1 text-xs text-muted">
            Look up an evaluation run by its ID to view its execution status and results.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <div className="space-y-2">
              <span className="block text-sm font-medium" id="evaluation-run-id-label">
                Evaluation run ID
              </span>
              <Selector
                allowCustomValue
                id="evaluation-run-id"
                loading={evaluationRunsQuery.isFetching}
                mode="single"
                onChange={(val) => setLookupRunId(String(val || ""))}
                options={evaluationRunOptions}
                placeholder="Select an evaluation run..."
                searchPlaceholder="Search run name or ID..."
                value={lookupRunId}
              />
            </div>
            <Button className="self-end" onClick={handleLookup} type="button">
              <Search aria-hidden="true" className="size-4" />
              Load status
            </Button>
          </div>
        </CardContent>
      </Card>

      {status.isLoading || status.isFetching ? (
        <EvaluationLoadingState />
      ) : status.data ? (
        <>
          <EvaluationStatusCard status={status.data} />
          <EvaluationMetrics summary={status.data.summary} />
          <EvaluationReport
            isFetching={report.isFetching}
            markdown={report.data ?? null}
          />
        </>
      ) : (
        <EmptyState
          description="Start an evaluation or load an existing run ID to inspect status."
          icon={<BarChart3 aria-hidden="true" className="size-5" />}
          title="No evaluation selected"
        />
      )}
    </div>
  );
}

function EvaluationLoadingState() {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <Skeleton className="h-4 w-44" />
            <Skeleton className="h-3 w-20" />
          </div>
          <Skeleton className="h-5 w-20" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              className="rounded-md border border-border bg-panel-muted p-3 space-y-2"
              key={index}
            >
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-20" />
          <div className="flex flex-wrap gap-2">
            <Skeleton className="h-6 w-24 rounded-md" />
            <Skeleton className="h-6 w-28 rounded-md" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function EvaluationStatusCard({ status }: { status: EvaluationStatusResponse }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-sm font-semibold">{status.name}</h2>
            <p className="mt-1 font-mono text-xs text-muted">
              Run {status.evaluation_run_id}
            </p>
          </div>
          <Badge tone={status.status === "completed" ? "success" : "warning"}>
            {formatSnakeCase(status.status)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Commit limit" value={String(status.commit_limit)} />
          <Metric label="Methods" value={String(status.methods.length)} />
          <Metric label="Repository" value={String(status.repository_id)} />
        </div>
        {status.error_message ? (
          <Notice tone="danger">{status.error_message}</Notice>
        ) : null}
        <div>
          <h3 className="text-sm font-semibold">
            <TermTooltip
              description="Collection of analysis techniques and algorithm variants evaluated in this benchmark run."
              term="Methods"
            />
          </h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {status.methods.map((method) => {
              const desc =
                METHOD_DESCRIPTIONS[method] || `Evaluation algorithm: ${method}`;
              return (
                <span
                  className="rounded-md border border-border bg-panel-muted px-2 py-1 font-mono text-xs text-muted"
                  key={method}
                >
                  <TermTooltip description={desc} term={formatSnakeCase(method)} />
                </span>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function EvaluationMetrics({ summary }: { summary: Record<string, unknown> }) {
  const chartData = buildMetricRows(summary);
  const topMetrics = chartData.slice(0, 4);

  if (chartData.length === 0) {
    return (
      <EmptyState
        description="This evaluation status did not include numeric metric summary data."
        icon={<BarChart3 aria-hidden="true" className="size-5" />}
        title="No metrics returned"
      />
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Metrics summary</h2>
          <p className="mt-1 text-xs text-muted">
            Top retrieval and prediction accuracy scores across tested methods.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {topMetrics.map((metric) => (
              <Metric
                key={`${metric.method}:${metric.metric}`}
                label={`${formatSnakeCase(metric.method)} ${formatSnakeCase(metric.metric)}`}
                value={formatPercent(metric.value)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Baseline comparison</h2>
          <p className="mt-1 text-xs text-muted">
            Comparative performance bar chart across evaluation algorithms.
          </p>
        </CardHeader>
        <CardContent>
          <div className="h-64 min-w-0">
            <ResponsiveContainer height="100%" minWidth={300} width="100%">
              <BarChart
                data={chartData.slice(0, 8)}
                margin={{ bottom: 20, left: 10, right: 10, top: 8 }}
              >
                <CartesianGrid stroke="rgb(var(--color-border))" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="label"
                  fontSize={11}
                  interval={0}
                  stroke="rgb(var(--color-muted))"
                  tickMargin={8}
                  tickLine={false}
                >
                  <Label
                    fill="rgb(var(--color-muted))"
                    fontSize={11}
                    offset={-12}
                    position="insideBottom"
                    value="Tested Algorithm / Metric"
                  />
                </XAxis>
                <YAxis
                  axisLine={false}
                  domain={[0, 1]}
                  fontSize={11}
                  stroke="rgb(var(--color-muted))"
                  tickMargin={8}
                  tickLine={false}
                >
                  <Label
                    angle={-90}
                    fill="rgb(var(--color-muted))"
                    fontSize={11}
                    position="insideLeft"
                    style={{ textAnchor: "middle" }}
                    value="Score (%)"
                  />
                </YAxis>
                <Tooltip
                  contentStyle={{
                    background: "rgb(var(--color-panel))",
                    border: "1px solid rgb(var(--color-border))",
                    borderRadius: 8,
                    color: "rgb(var(--color-foreground))",
                  }}
                  cursor={{ fill: "rgb(var(--color-panel-muted))" }}
                />
                <Bar
                  barSize={32}
                  dataKey="value"
                  fill="rgb(var(--color-chart-a))"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function EvaluationReport({
  isFetching,
  markdown,
}: {
  isFetching: boolean;
  markdown: string | null;
}) {
  if (isFetching) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-36" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  if (!markdown) {
    return (
      <EmptyState
        description="No Markdown report is available for the selected evaluation run yet."
        icon={<BarChart3 aria-hidden="true" className="size-5" />}
        title="No report available"
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold">Markdown report</h2>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 text-sm leading-6 text-muted [&_code]:rounded [&_code]:bg-panel-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:text-foreground [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-foreground [&_li]:ml-5 [&_li]:list-disc [&_p]:text-muted [&_strong]:text-foreground">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  );
}

function buildMetricRows(summary: Record<string, unknown>) {
  return Object.entries(summary).flatMap(([method, value]) =>
    flattenMetrics(value).map((metric) => ({
      label: `${method}:${metric.name}`,
      method,
      metric: metric.name,
      value: metric.value,
    })),
  );
}

function flattenMetrics(
  value: unknown,
  prefix = "",
): { name: string; value: number }[] {
  if (typeof value === "number" && Number.isFinite(value)) {
    return [{ name: prefix || "score", value }];
  }

  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return [];
  }

  return Object.entries(value).flatMap(([key, nested]) =>
    flattenMetrics(nested, prefix ? `${prefix}.${key}` : key),
  );
}

const EVALUATION_METRIC_DESCRIPTIONS: Record<string, string> = {
  "Commit limit": "Maximum number of git commits evaluated during this benchmark run.",
  Methods: "Number of retrieval algorithms tested in this evaluation run.",
  Repository: "Unique identifier of the target codebase.",
};

function Metric({
  description,
  label,
  value,
}: {
  description?: string;
  label: string;
  value: string;
}) {
  const desc = description || EVALUATION_METRIC_DESCRIPTIONS[label];

  return (
    <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {desc ? <TermTooltip description={desc} term={label} /> : label}
      </div>
      <div className="mt-1 break-all font-mono text-sm font-semibold">{value}</div>
    </div>
  );
}

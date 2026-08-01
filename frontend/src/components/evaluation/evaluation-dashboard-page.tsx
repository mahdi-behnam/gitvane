"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { BarChart3, Play, RefreshCw, Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { EvaluationMethod, EvaluationStatusResponse } from "@/lib/api/types";
import {
  useGetEvaluationReportMarkdownQuery,
  useGetEvaluationStatusQuery,
  useGetRepositoryQuery,
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

function parseKValues(value: string) {
  return value
    .split(",")
    .map((part) => Number(part.trim()))
    .filter((value) => Number.isFinite(value) && value > 0);
}

export function EvaluationDashboardPage({ repositoryId }: { repositoryId: string }) {
  const validRepositoryId = typeof repositoryId === "string" && repositoryId.trim() !== "" ? repositoryId : null;
  const [name, setName] = useState("Repository evaluation");
  const [commitLimit, setCommitLimit] = useState(50);
  const [kValues, setKValues] = useState("5,10,20");
  const [methods, setMethods] = useState<EvaluationMethod[]>(["hybrid"]);
  const [lookupRunId, setLookupRunId] = useState("");
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const [runEvaluation, runState] = useRunEvaluationMutation();
  const status = useGetEvaluationStatusQuery(activeRunId ?? skipToken);
  const report = useGetEvaluationReportMarkdownQuery(activeRunId ?? skipToken);
  const dispatch = useAppDispatch();

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

    if (methods.length === 0) {
      setClientError("Select at least one evaluation method.");
      return;
    }

    const parsedKValues = parseKValues(kValues);
    if (parsedKValues.length === 0) {
      setClientError("Enter at least one positive k value.");
      return;
    }

    setClientError(null);
    try {
      const response = await runEvaluation({
        commit_limit: commitLimit,
        k_values: parsedKValues,
        methods,
        name: name.trim() || undefined,
        repository_id: validRepositoryId,
      }).unwrap();
      setActiveRunId(response.evaluation_run_id);
      setLookupRunId(String(response.evaluation_run_id));
    } catch {
      // The normalized API message is rendered from mutation state.
    }
  };

  const handleLookup = () => {
    const parsedRunId = Number(lookupRunId);
    if (!Number.isInteger(parsedRunId) || parsedRunId <= 0) {
      setClientError("Enter a valid evaluation run ID.");
      return;
    }

    setClientError(null);
    setActiveRunId(parsedRunId);
  };

  const toggleMethod = (method: EvaluationMethod) => {
    setMethods((current) =>
      current.includes(method)
        ? current.filter((currentMethod) => currentMethod !== method)
        : [...current, method],
    );
  };

  const apiError =
    (runState.error && normalizeApiError(runState.error).message) ||
    (status.error && normalizeApiError(status.error).message) ||
    (report.error && normalizeApiError(report.error).message) ||
    null;
  const error = clientError ?? apiError;

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
          <Badge tone="info">Evaluation</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            Evaluation dashboard
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Run historical prediction evaluations, inspect status manually, and review
            reported quality metrics when the backend has generated them.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Run evaluation</h2>
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
                  value={name}
                />
              </div>
              <div className="space-y-2">
                <label
                  className="block text-sm font-medium"
                  htmlFor="evaluation-commit-limit"
                >
                  Commit limit
                </label>
                <Input
                  id="evaluation-commit-limit"
                  min={1}
                  onChange={(event) => setCommitLimit(Number(event.target.value))}
                  type="number"
                  value={commitLimit}
                />
              </div>
              <div className="space-y-2">
                <label
                  className="block text-sm font-medium"
                  htmlFor="evaluation-k-values"
                >
                  K values
                </label>
                <Input
                  id="evaluation-k-values"
                  onChange={(event) => setKValues(event.target.value)}
                  value={kValues}
                />
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium">Methods</p>
              <div className="flex flex-wrap gap-2">
                {evaluationMethods.map((method) => (
                  <label
                    className="flex h-9 items-center gap-2 rounded-md border border-border bg-panel px-3 text-sm"
                    key={method}
                  >
                    <input
                      checked={methods.includes(method)}
                      className="size-4 rounded border-border text-primary focus:ring-primary"
                      onChange={() => toggleMethod(method)}
                      type="checkbox"
                    />
                    {method}
                  </label>
                ))}
              </div>
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
          <h2 className="text-sm font-semibold">Manual refresh</h2>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="evaluation-run-id">
                Evaluation run ID
              </label>
              <Input
                id="evaluation-run-id"
                onChange={(event) => setLookupRunId(event.target.value)}
                placeholder="42"
                value={lookupRunId}
              />
            </div>
            <Button className="self-end" onClick={handleLookup} type="button">
              <Search aria-hidden="true" className="size-4" />
              Load status
            </Button>
            <Button
              className="self-end"
              disabled={!activeRunId || status.isFetching}
              onClick={() => status.refetch()}
              type="button"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
              Refresh
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
            {status.status}
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
          <h3 className="text-sm font-semibold">Methods</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {status.methods.map((method) => (
              <span
                className="rounded-md border border-border bg-panel-muted px-2 py-1 font-mono text-xs text-muted"
                key={method}
              >
                {method}
              </span>
            ))}
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
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {topMetrics.map((metric) => (
              <Metric
                key={`${metric.method}:${metric.metric}`}
                label={`${metric.method} ${metric.metric}`}
                value={metric.value.toFixed(3)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Baseline comparison</h2>
        </CardHeader>
        <CardContent>
          <div className="h-64 min-w-0">
            <ResponsiveContainer height="100%" minWidth={300} width="100%">
              <BarChart
                data={chartData.slice(0, 8)}
                margin={{ bottom: 0, left: -12, right: 8, top: 8 }}
              >
                <CartesianGrid stroke="rgb(var(--color-border))" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="label"
                  fontSize={12}
                  interval={0}
                  stroke="rgb(var(--color-muted))"
                  tickMargin={8}
                  tickLine={false}
                />
                <YAxis
                  axisLine={false}
                  domain={[0, 1]}
                  fontSize={12}
                  stroke="rgb(var(--color-muted))"
                  tickMargin={8}
                  tickLine={false}
                />
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {label}
      </div>
      <div className="mt-1 break-all font-mono text-sm font-semibold">{value}</div>
    </div>
  );
}

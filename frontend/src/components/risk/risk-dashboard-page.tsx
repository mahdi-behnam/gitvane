"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { Filter, RefreshCw, ShieldAlert } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/table";
import { normalizeApiError } from "@/lib/api/errors";
import type { RiskFile } from "@/lib/api/types";
import {
  useGetRepositoryQuery,
  useGetRepositoryRiskQuery,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

type RiskFilters = {
  includeTests: boolean;
  language: string;
  topK: number;
};

const defaultFilters: RiskFilters = {
  includeTests: false,
  language: "",
  topK: 20,
};

export function RiskDashboardPage({ repositoryId }: { repositoryId: number }) {
  const validRepositoryId = Number.isFinite(repositoryId) ? repositoryId : null;
  const [draftFilters, setDraftFilters] = useState(defaultFilters);
  const [appliedFilters, setAppliedFilters] = useState(defaultFilters);
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const riskQueryArgs = validRepositoryId
    ? {
        include_tests: appliedFilters.includeTests,
        language: appliedFilters.language.trim() || null,
        repositoryId: validRepositoryId,
        top_k: appliedFilters.topK,
      }
    : skipToken;
  const risk = useGetRepositoryRiskQuery(riskQueryArgs);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedFilters({
      includeTests: draftFilters.includeTests,
      language: draftFilters.language.trim(),
      topK: Math.max(1, draftFilters.topK),
    });
  };

  const files = useMemo(() => risk.data?.files ?? [], [risk.data?.files]);
  const error = risk.error ? normalizeApiError(risk.error).message : null;
  const chartData = useMemo(() => buildRiskBuckets(files), [files]);
  const topComponents = useMemo(() => summarizeComponents(files), [files]);

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
          <Badge tone="warning">Risk</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Risk ranking</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Review heuristic file-level risk scores, component signals, and reasons from
            the current repository index.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <h2 className="text-sm font-semibold">Filters</h2>
            <Badge>Heuristic score</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 lg:grid-cols-[160px_1fr_auto_auto]"
            onSubmit={handleSubmit}
          >
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="risk-top-k">
                Top files
              </label>
              <Input
                id="risk-top-k"
                max={200}
                min={1}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    topK: Number(event.target.value),
                  }))
                }
                type="number"
                value={draftFilters.topK}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor="risk-language">
                Language filter
              </label>
              <Input
                id="risk-language"
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
              <Button disabled={risk.isFetching} type="submit" variant="primary">
                <Filter aria-hidden="true" className="size-4" />
                Apply
              </Button>
              <Button
                disabled={risk.isFetching}
                onClick={() => risk.refetch()}
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
        </CardContent>
      </Card>

      {risk.isLoading ? (
        <RiskLoadingState />
      ) : files.length > 0 ? (
        <>
          <RiskSummary files={files} chartData={chartData} components={topComponents} />
          <RiskTable files={files} />
        </>
      ) : risk.isSuccess ? (
        <EmptyState
          description="The backend did not return risk-ranked files for these filters."
          icon={<ShieldAlert aria-hidden="true" className="size-5" />}
          title="No risk results"
        />
      ) : (
        <EmptyState
          description="Risk data will load from the repository risk endpoint."
          icon={<ShieldAlert aria-hidden="true" className="size-5" />}
          title="Risk ranking"
        />
      )}
    </div>
  );
}

function buildRiskBuckets(files: RiskFile[]) {
  const buckets = [
    { count: 0, label: "0.00-0.25" },
    { count: 0, label: "0.25-0.50" },
    { count: 0, label: "0.50-0.75" },
    { count: 0, label: "0.75-1.00" },
  ];

  files.forEach((file) => {
    const score = Math.max(0, Math.min(1, file.risk_score));
    const index = Math.min(3, Math.floor(score * 4));
    buckets[index].count += 1;
  });

  return buckets;
}

function summarizeComponents(files: RiskFile[]) {
  const totals = new Map<string, number>();

  files.forEach((file) => {
    Object.entries(file.components).forEach(([name, value]) => {
      totals.set(name, (totals.get(name) ?? 0) + value);
    });
  });

  return Array.from(totals.entries())
    .map(([name, value]) => ({
      name,
      value: files.length > 0 ? value / files.length : 0,
    }))
    .sort((left, right) => right.value - left.value)
    .slice(0, 4);
}

function RiskLoadingState() {
  return (
    <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card className="p-5">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="mt-5 h-56 w-full" />
      </Card>
      <Card className="p-5">
        <Skeleton className="h-4 w-44" />
        <Skeleton className="mt-5 h-56 w-full" />
      </Card>
    </div>
  );
}

function RiskSummary({
  chartData,
  components,
  files,
}: {
  chartData: ReturnType<typeof buildRiskBuckets>;
  components: ReturnType<typeof summarizeComponents>;
  files: RiskFile[];
}) {
  const averageRisk =
    files.reduce((total, file) => total + file.risk_score, 0) / files.length;
  const highestRisk = files[0];

  return (
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Risk summary</h2>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Files" value={String(files.length)} />
            <Metric label="Average" value={averageRisk.toFixed(3)} />
            <Metric label="Highest" value={highestRisk.risk_score.toFixed(3)} />
          </div>
          <div className="mt-5 space-y-3">
            <h3 className="text-sm font-semibold">Top component signals</h3>
            {components.length > 0 ? (
              components.map((component) => (
                <div className="space-y-1" key={component.name}>
                  <div className="flex justify-between gap-3 text-xs">
                    <span className="font-mono text-muted">{component.name}</span>
                    <span className="font-mono">{component.value.toFixed(3)}</span>
                  </div>
                  <div className="h-2 rounded-sm bg-panel-muted">
                    <div
                      className="h-2 rounded-sm bg-primary"
                      style={{ width: `${Math.min(100, component.value * 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No component values returned.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Risk distribution</h2>
        </CardHeader>
        <CardContent>
          <div className="h-64 min-w-0">
            <ResponsiveContainer height="100%" minWidth={300} width="100%">
              <BarChart data={chartData}>
                <CartesianGrid stroke="rgb(var(--color-border))" vertical={false} />
                <XAxis
                  dataKey="label"
                  fontSize={12}
                  stroke="rgb(var(--color-muted))"
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  fontSize={12}
                  stroke="rgb(var(--color-muted))"
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgb(var(--color-panel))",
                    border: "1px solid rgb(var(--color-border))",
                    borderRadius: 8,
                    color: "rgb(var(--color-foreground))",
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="rgb(var(--color-chart-b))"
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

function RiskTable({ files }: { files: RiskFile[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-sm font-semibold">Ranked files</h2>
          <Badge>{files.length} files</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell className="w-20">Rank</TableHeaderCell>
              <TableHeaderCell>File</TableHeaderCell>
              <TableHeaderCell className="w-28 text-right">Risk</TableHeaderCell>
              <TableHeaderCell>Components</TableHeaderCell>
              <TableHeaderCell>Reasons</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {files.map((file, index) => (
              <TableRow key={file.path}>
                <TableCell className="font-mono text-xs text-muted">
                  #{index + 1}
                </TableCell>
                <TableCell>
                  <span className="break-all font-mono text-sm font-semibold">
                    {file.path}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">
                  {file.risk_score.toFixed(3)}
                </TableCell>
                <TableCell>
                  <ComponentDetails components={file.components} />
                </TableCell>
                <TableCell>
                  <ReasonList reasons={file.reasons} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ComponentDetails({ components }: { components: Record<string, number> }) {
  const entries = Object.entries(components).sort((left, right) => right[1] - left[1]);

  if (entries.length === 0) {
    return <span className="text-sm text-muted">No components</span>;
  }

  return (
    <div className="min-w-48 space-y-2">
      {entries.map(([name, value]) => (
        <div className="space-y-1" key={name}>
          <div className="flex justify-between gap-3 text-xs">
            <span className="font-mono text-muted">{name}</span>
            <span className="font-mono">{value.toFixed(3)}</span>
          </div>
          <div className="h-1.5 rounded-sm bg-panel-muted">
            <div
              className="h-1.5 rounded-sm bg-primary"
              style={{ width: `${Math.min(100, Math.max(0, value) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ReasonList({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) {
    return <span className="text-sm text-muted">No reasons returned.</span>;
  }

  return (
    <ul className="max-w-xl space-y-1 text-sm leading-6 text-muted">
      {reasons.map((reason) => (
        <li key={reason}>{reason}</li>
      ))}
    </ul>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {label}
      </div>
      <div className="mt-1 font-mono text-lg font-semibold">{value}</div>
    </div>
  );
}

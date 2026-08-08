"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { AlertCircle, Check, Copy, FlaskConical, GitGraph, Filter, RefreshCw, ShieldAlert, X, Zap } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/table";
import { FileSelector } from "@/components/ui/file-selector";
import { Selector, SelectorOption } from "@/components/ui/selector";
import { normalizeApiError } from "@/lib/api/errors";
import type { RepositoryRiskResponse, RiskFile } from "@/lib/api/types";
import { formatSnakeCase, formatTitleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  useGetRepositoryLanguagesQuery,
  useGetRepositoryQuery,
  useGetRepositoryRiskQuery,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

type RiskFilters = {
  includeTests: boolean;
  language: string;
  search: string;
  topK: number;
};

const defaultFilters: RiskFilters = {
  includeTests: false,
  language: "",
  search: "",
  topK: 20,
};

export function RiskDashboardPage({
  initialPath,
  repositoryId,
}: {
  initialPath?: string;
  repositoryId: string;
}) {
  const validRepositoryId = typeof repositoryId === "string" && repositoryId.trim() !== "" ? repositoryId : null;
  const searchParams = useSearchParams();

  const [draftFilters, setDraftFilters] = useState<RiskFilters>(() => {
    const search = initialPath ?? searchParams?.get("path") ?? searchParams?.get("search") ?? searchParams?.get("query") ?? "";
    const includeTests = searchParams?.get("include_tests") === "true";
    const language = searchParams?.get("language") ?? "";
    const topKRaw = searchParams?.get("top_k");
    const topK = topKRaw && !isNaN(Number(topKRaw)) ? Number(topKRaw) : 20;
    return { includeTests, language, search, topK };
  });

  const [appliedFilters, setAppliedFilters] = useState<RiskFilters>(() => {
    const search = initialPath ?? searchParams?.get("path") ?? searchParams?.get("search") ?? searchParams?.get("query") ?? "";
    const includeTests = searchParams?.get("include_tests") === "true";
    const language = searchParams?.get("language") ?? "";
    const topKRaw = searchParams?.get("top_k");
    const topK = topKRaw && !isNaN(Number(topKRaw)) ? Number(topKRaw) : 20;
    return { includeTests, language, search, topK };
  });

  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const languagesQuery = useGetRepositoryLanguagesQuery(validRepositoryId ?? skipToken);
  const riskQueryArgs = validRepositoryId
    ? {
        include_tests: appliedFilters.includeTests,
        language: appliedFilters.language.trim() || null,
        path_search: appliedFilters.search.trim() || null,
        repositoryId: validRepositoryId,
        top_k: appliedFilters.topK,
      }
    : skipToken;
  const risk = useGetRepositoryRiskQuery(riskQueryArgs);

  const languageOptions: SelectorOption[] = useMemo(() => {
    const langs = languagesQuery.data ?? [];
    return [
      { label: "All languages", value: "" },
      ...langs.map((lang) => ({ label: lang, value: lang })),
    ];
  }, [languagesQuery.data]);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  useEffect(() => {
    if (initialPath) {
      setDraftFilters((curr) => ({ ...curr, search: initialPath }));
      setAppliedFilters((curr) => ({ ...curr, search: initialPath }));
    }
  }, [initialPath]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedFilters({
      includeTests: draftFilters.includeTests,
      language: draftFilters.language.trim(),
      search: draftFilters.search.trim(),
      topK: Math.max(1, draftFilters.topK),
    });
  };

  const handleFileSelect = (val: string | string[]) => {
    const selected = String(val || "").trim();
    setDraftFilters((current) => ({ ...current, search: selected }));
    setAppliedFilters((current) => ({ ...current, search: selected }));
  };

  const handleResetFilters = () => {
    setDraftFilters(defaultFilters);
    setAppliedFilters(defaultFilters);
  };

  const handleRemoveFilter = (key: keyof RiskFilters) => {
    const updated = { ...appliedFilters, [key]: defaultFilters[key] };
    setDraftFilters(updated);
    setAppliedFilters(updated);
  };

  const files = useMemo(() => {
    const rawFiles = risk.data?.files ?? [];
    if (!appliedFilters.search) return rawFiles;
    const query = appliedFilters.search.toLowerCase();
    return rawFiles.filter((file) => file.path.toLowerCase().includes(query));
  }, [risk.data?.files, appliedFilters.search]);

  const isSingleFileMode = Boolean(appliedFilters.search.trim());

  const hasActiveFilters =
    appliedFilters.includeTests !== defaultFilters.includeTests ||
    appliedFilters.language !== defaultFilters.language ||
    appliedFilters.search !== defaultFilters.search ||
    appliedFilters.topK !== defaultFilters.topK;

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
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold md:text-4xl">Risk ranking</h1>
            <Badge tone="neutral">
              <TermTooltip
                description="Calculated deterministically using structural dependency analysis, cyclomatic complexity, and git change metrics without LLM non-determinism."
                term="Deterministic Heuristic Scoring"
              />
            </Badge>
          </div>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
            Identify high-risk files in your codebase calculated from change frequency (churn),
            cyclomatic complexity, and structural dependency connections (fan-in / fan-out).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
            {repository.data?.name ?? `Repository ${validRepositoryId}`}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Filters</h2>
              <p className="mt-1 text-xs text-muted">
                Filter repository files by risk threshold, path keywords, or result limits.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 items-end lg:grid-cols-[140px_1fr_1fr_auto_auto]"
            onSubmit={handleSubmit}
          >
            <div
              className="space-y-2"
              title={draftFilters.search ? "Bypassed/disabled during single-file inspection mode" : undefined}
            >
              <label className="flex items-center gap-1 text-sm font-medium" htmlFor="risk-top-k">
                <TermTooltip
                  description="Maximum number of highest-risk repository files to evaluate and display."
                  term="Top files"
                />
              </label>
              <Input
                disabled={Boolean(draftFilters.search)}
                id="risk-top-k"
                max={200}
                min={1}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    topK: Number(event.target.value),
                  }))
                }
                title={draftFilters.search ? "Bypassed/disabled during single-file inspection mode" : undefined}
                type="number"
                value={draftFilters.topK}
              />
            </div>
            <div className="space-y-2">
              <span className="block text-sm font-medium" id="risk-search-label">
                File search
              </span>
              <FileSelector
                id="risk-search"
                language={draftFilters.language}
                mode="single"
                onChange={handleFileSelect}
                placeholder="All files (select path...)"
                repositoryId={validRepositoryId ?? ""}
                value={draftFilters.search}
              />
            </div>
            <div
              className="space-y-2"
              title={draftFilters.search ? "Bypassed/disabled during single-file inspection mode" : undefined}
            >
              <span className="block text-sm font-medium" id="risk-language-label">
                Language filter
              </span>
              <Selector
                allowCustomValue
                disabled={Boolean(draftFilters.search)}
                id="risk-language"
                loading={languagesQuery.isFetching}
                mode="single"
                onChange={(val) =>
                  setDraftFilters((current) => ({
                    ...current,
                    language: String(val || ""),
                  }))
                }
                options={languageOptions}
                placeholder="All languages"
                searchPlaceholder="Type language..."
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
              <TermTooltip
                description="Include test files (e.g. test_*.py, *.spec.ts) in the calculated risk ranking."
                term="Include tests"
              />
            </label>
            <div className="flex gap-2 self-end">
              <Button disabled={risk.isFetching} type="submit" variant="primary">
                <Filter aria-hidden="true" className="size-4" />
                Apply
              </Button>
            </div>
          </form>

          {hasActiveFilters ? (
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3 text-xs">
              <span className="font-medium text-muted">Active filters:</span>
              {appliedFilters.search ? (
                <Badge className="normal-case font-medium flex items-center gap-1 font-mono" tone="neutral">
                  Search: {appliedFilters.search}
                  <button
                    aria-label="Remove search filter"
                    className="ml-1 text-muted hover:text-foreground"
                    onClick={() => handleRemoveFilter("search")}
                    type="button"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ) : null}
              {appliedFilters.language ? (
                <Badge className="normal-case font-medium flex items-center gap-1" tone="neutral">
                  Language: {appliedFilters.language}
                  <button
                    aria-label="Remove language filter"
                    className="ml-1 text-muted hover:text-foreground"
                    onClick={() => handleRemoveFilter("language")}
                    type="button"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ) : null}
              {appliedFilters.topK !== defaultFilters.topK ? (
                <Badge className="normal-case font-medium flex items-center gap-1 font-mono" tone="neutral">
                  Top Files: {appliedFilters.topK}
                  <button
                    aria-label="Remove top files filter"
                    className="ml-1 text-muted hover:text-foreground"
                    onClick={() => handleRemoveFilter("topK")}
                    type="button"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ) : null}
              {appliedFilters.includeTests ? (
                <Badge className="normal-case font-medium flex items-center gap-1" tone="neutral">
                  Include Tests: Yes
                  <button
                    aria-label="Remove include tests filter"
                    className="ml-1 text-muted hover:text-foreground"
                    onClick={() => handleRemoveFilter("includeTests")}
                    type="button"
                  >
                    <X className="size-3" />
                  </button>
                </Badge>
              ) : null}
              <Button
                className="h-6 px-2 text-xs border-danger/40 text-danger hover:bg-danger/10 hover:border-danger/60 hover:text-danger"
                onClick={handleResetFilters}
                size="sm"
                type="button"
                variant="secondary"
              >
                <X className="mr-1 size-3" />
                Reset filters
              </Button>
            </div>
          ) : null}

          {error ? (
            <Notice className="mt-4" tone="danger">
              {error}
            </Notice>
          ) : null}
        </CardContent>
      </Card>

      <div className={cn("space-y-6 transition-opacity duration-200", risk.isFetching && !risk.isLoading && "opacity-60 pointer-events-none")}>
        {risk.isLoading ? (
          <RiskLoadingState />
        ) : files.length > 0 ? (
          <>
            <RiskSummary
              chartData={chartData}
              components={topComponents}
              files={files}
              isSingleFileMode={isSingleFileMode}
              metadata={risk.data?.metadata}
            />
            <RiskTable files={files} isSingleFileMode={isSingleFileMode} repositoryId={validRepositoryId} />
          </>
        ) : risk.isSuccess ? (
          <EmptyState
            action={
              hasActiveFilters ? (
                <Button onClick={handleResetFilters} type="button" variant="secondary">
                  Clear filters & search
                </Button>
              ) : undefined
            }
            description="No risk-ranked files found for these filters."
            icon={<ShieldAlert aria-hidden="true" className="size-5" />}
            title="No risk results"
          />
        ) : (
          <EmptyState
            description="Risk data will load once the repository metadata has been processed."
            icon={<ShieldAlert aria-hidden="true" className="size-5" />}
            title="Risk ranking"
          />
        )}
      </div>
    </div>
  );
}

function buildRiskBuckets(files: RiskFile[]) {
  const buckets = [
    { count: 0, label: "0% - 25% (Low)" },
    { count: 0, label: "25% - 50% (Moderate)" },
    { count: 0, label: "50% - 75% (High)" },
    { count: 0, label: "75% - 100% (Critical)" },
  ];

  files.forEach((file) => {
    const score = Math.max(0, Math.min(1, file.risk_score));
    const index = Math.min(3, Math.floor(score * 4));
    buckets[index].count += 1;
  });

  return buckets;
}

function buildSingleFileSignalBreakdown(file: RiskFile, metadata?: RepositoryRiskResponse["metadata"]) {
  const breakdown = metadata?.single_file_breakdown;
  const loc = breakdown?.loc ?? Math.round((file.components.file_size ?? 0) * 500);
  const fanIn = breakdown?.fan_in ?? Math.round((file.components.fan_in ?? 0) * 10);
  const fanOut = breakdown?.fan_out ?? Math.round((file.components.fan_out ?? 0) * 10);
  const centrality = Math.round((file.components.centrality ?? 0) * 20);
  const churn = breakdown?.churn_commit_count ?? Math.round((file.components.churn ?? 0) * 20);
  const complexity = breakdown?.complexity_score ?? (file.components.complexity ?? 0);
  const bugfixes = breakdown?.bugfix_count ?? Math.round((file.components.bugfix_frequency ?? 0) * 8);
  const testCoverage = Math.round((file.components.test_coverage_proxy ?? 0) * 100);

  return [
    { label: "Lines of Code", raw: `${loc} LOC`, score: Math.round((file.components.file_size ?? 0) * 100) },
    { label: "Fan In", raw: `${fanIn} incoming`, score: Math.round((file.components.fan_in ?? 0) * 100) },
    { label: "Fan Out", raw: `${fanOut} outgoing`, score: Math.round((file.components.fan_out ?? 0) * 100) },
    { label: "Centrality", raw: `${centrality} degree`, score: Math.round((file.components.centrality ?? 0) * 100) },
    { label: "Churn", raw: `${churn} commits`, score: Math.round((file.components.churn ?? 0) * 100) },
    { label: "Complexity", raw: `${complexity.toFixed(1)} score`, score: Math.round((file.components.complexity ?? 0) * 100) },
    { label: "Bugfixes", raw: `${bugfixes} fixes`, score: Math.round((file.components.bugfix_frequency ?? 0) * 100) },
    { label: "Test Proximity", raw: `${testCoverage}% proxy`, score: Math.round((file.components.test_coverage_proxy ?? 0) * 100) },
  ];
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
  isSingleFileMode,
  metadata,
}: {
  chartData: ReturnType<typeof buildRiskBuckets>;
  components: ReturnType<typeof summarizeComponents>;
  files: RiskFile[];
  isSingleFileMode?: boolean;
  metadata?: RepositoryRiskResponse["metadata"];
}) {
  const averageRisk =
    typeof metadata?.mean_risk_score === "number"
      ? metadata.mean_risk_score
      : files.length > 0
      ? files.reduce((total, file) => total + file.risk_score, 0) / files.length
      : 0;

  if (isSingleFileMode && files.length > 0) {
    const file = files[0];
    const score = file.risk_score;
    const severityBadge =
      score >= 0.75 ? (
        <Badge tone="danger">Critical Risk</Badge>
      ) : score >= 0.5 ? (
        <Badge tone="warning">High Risk</Badge>
      ) : score >= 0.25 ? (
        <Badge tone="info">Moderate Risk</Badge>
      ) : (
        <Badge tone="neutral">Low Risk</Badge>
      );

    const diffVal = (score - averageRisk) * 100;
    const diffAbs = Math.abs(diffVal).toFixed(1);
    const varianceLabel =
      diffVal > 0.05
        ? `+${diffAbs}% above avg`
        : diffVal < -0.05
        ? `-${diffAbs}% below avg`
        : `0.0% (equal to avg)`;

    const varianceColor =
      diffVal > 0.05
        ? "text-rose-500 font-semibold"
        : diffVal < -0.05
        ? "text-emerald-500 font-semibold"
        : "text-muted font-normal";

    const sortedComponents = Object.entries(file.components).sort((a, b) => b[1] - a[1]);
    const topComp = sortedComponents[0];
    const primaryDriver = topComp
      ? `${COMPONENT_DESCRIPTIONS[topComp[0]]?.label || formatTitleCase(formatSnakeCase(topComp[0]))} (${(topComp[1] * 100).toFixed(1)}%)`
      : "None";

    const singleFileSignals = buildSingleFileSignalBreakdown(file, metadata);

    return (
      <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">File risk summary</h2>
              {severityBadge}
            </div>
            <p className="mt-1 text-xs text-muted">
              Heuristic risk metrics and comparative architectural analysis for selected file.
            </p>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-3">
              <Metric
                description="Calculated heuristic risk score percentage for this file."
                label="File Risk Score"
                value={`${(score * 100).toFixed(1)}%`}
              />
              <Metric
                description="Risk score variance relative to average repository score."
                label="Vs Repo Average"
                value={<span className={varianceColor}>{varianceLabel}</span>}
              />
              <Metric
                description="Highest component signal contributing to this file's risk calculation."
                label="Primary Driver"
                value={primaryDriver}
              />
            </div>
            <div className="mt-5 space-y-3">
              <h3 className="text-sm font-semibold">Component signals</h3>
              {sortedComponents.map(([name, value]) => {
                const info = COMPONENT_DESCRIPTIONS[name] || {
                  label: formatTitleCase(formatSnakeCase(name)),
                  desc: `Component signal weight for ${formatTitleCase(formatSnakeCase(name))}.`,
                };
                return (
                  <div className="space-y-1" key={name}>
                    <div className="flex justify-between gap-3 text-xs">
                      <TermTooltip description={info.desc} term={info.label} />
                      <span className="font-mono">{(value * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full rounded-sm bg-background border border-border/80 dark:bg-slate-950 dark:border-slate-700/80 overflow-hidden shadow-inner">
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${Math.min(100, Math.max(0, value) * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">File signal breakdown</h2>
            <p className="mt-1 text-xs text-muted">
              Structural and change signals showing raw metric counts and percentage component weights.
            </p>
          </CardHeader>
          <CardContent>
            <div className="h-64 min-w-0">
              <ResponsiveContainer height="100%" minWidth={300} width="100%">
                <BarChart
                  data={singleFileSignals}
                  layout="vertical"
                  margin={{ bottom: 10, left: 30, right: 20, top: 10 }}
                >
                  <CartesianGrid horizontal={false} stroke="rgb(var(--color-border))" />
                  <XAxis
                    domain={[0, 100]}
                    fontSize={11}
                    stroke="rgb(var(--color-muted))"
                    tickFormatter={(val) => `${val}%`}
                    type="number"
                  />
                  <YAxis
                    dataKey="label"
                    fontSize={11}
                    stroke="rgb(var(--color-muted))"
                    type="category"
                    width={90}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="rounded-md border border-border bg-panel p-2 text-xs shadow-md">
                            <p className="font-semibold">{data.label}</p>
                            <p className="text-muted">Raw: {data.raw}</p>
                            <p className="font-mono font-medium text-primary">Weight: {data.score}%</p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar
                    barSize={20}
                    dataKey="score"
                    fill="rgb(var(--color-chart-b))"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </section>
    );
  }

  const highestRisk = files[0];

  return (
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Risk summary</h2>
          <p className="mt-1 text-xs text-muted">
            Overview of total file count, average risk score, and top architectural signal weights.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric
              description="Total number of repository source files included in this risk assessment."
              label="Files"
              value={String(files.length)}
            />
            <Metric
              description="Mean calculated risk percentage across all evaluated repository files."
              label="Average"
              value={`${(averageRisk * 100).toFixed(1)}%`}
            />
            <Metric
              description="Risk percentage of the most critical file identified in the current index."
              label="Highest"
              value={`${((highestRisk?.risk_score ?? 0) * 100).toFixed(1)}%`}
            />
          </div>
          <div className="mt-5 space-y-3">
            <h3 className="text-sm font-semibold">Top component signals</h3>
            {components.length > 0 ? (
              components.map((component) => {
                const info = COMPONENT_DESCRIPTIONS[component.name] || {
                  label: formatTitleCase(formatSnakeCase(component.name)),
                  desc: `Average component signal weight for ${formatTitleCase(formatSnakeCase(component.name))}.`,
                };

                return (
                  <div className="space-y-1" key={component.name}>
                    <div className="flex justify-between gap-3 text-xs">
                      <TermTooltip description={info.desc} term={info.label} />
                      <span className="font-mono">{(component.value * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full rounded-sm bg-background border border-border/80 dark:bg-slate-950 dark:border-slate-700/80 overflow-hidden shadow-inner">
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${Math.min(100, component.value * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-muted">No component values returned.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Risk distribution</h2>
          <p className="mt-1 text-xs text-muted">
            Histogram grouping files into risk level percentage buckets (0% to 100%).
          </p>
        </CardHeader>
        <CardContent>
          <div className="h-64 min-w-0">
            <ResponsiveContainer height="100%" minWidth={300} width="100%">
              <BarChart
                data={chartData}
                margin={{ bottom: 20, left: 10, right: 10, top: 8 }}
              >
                <CartesianGrid stroke="rgb(var(--color-border))" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="label"
                  fontSize={11}
                  stroke="rgb(var(--color-muted))"
                  tickLine={false}
                  tickMargin={8}
                >
                  <Label
                    fill="rgb(var(--color-muted))"
                    fontSize={11}
                    offset={-12}
                    position="insideBottom"
                    value="Risk Level Range (%)"
                  />
                </XAxis>
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  fontSize={11}
                  stroke="rgb(var(--color-muted))"
                  tickLine={false}
                  tickMargin={8}
                >
                  <Label
                    angle={-90}
                    fill="rgb(var(--color-muted))"
                    fontSize={11}
                    position="insideLeft"
                    style={{ textAnchor: "middle" }}
                    value="File Count"
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
                  barSize={36}
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

function CopyPathButton({ path }: { path: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard.writeText(path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      aria-label="Copy file path"
      className="size-7"
      onClick={handleCopy}
      size="icon"
      title="Copy file path"
      type="button"
      variant="ghost"
    >
      {copied ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
    </Button>
  );
}

function RiskTable({
  files,
  isSingleFileMode,
  repositoryId,
}: {
  files: RiskFile[];
  isSingleFileMode?: boolean;
  repositoryId: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-sm font-semibold">{isSingleFileMode ? "Inspected file" : "Ranked files"}</h2>
            <p className="mt-1 text-xs text-muted">
              {isSingleFileMode
                ? "Detailed risk analysis and component breakdown for the selected file."
                : "Source files ordered by calculated risk score with detailed component breakdowns."}
            </p>
          </div>
          <span className="text-xs text-muted font-medium">{files.length} {files.length === 1 ? "file" : "files"}</span>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHead>
            <TableRow>
              {!isSingleFileMode ? <TableHeaderCell className="w-16">Rank</TableHeaderCell> : null}
              <TableHeaderCell>File</TableHeaderCell>
              <TableHeaderCell className="w-24 text-right">Risk</TableHeaderCell>
              <TableHeaderCell>Components</TableHeaderCell>
              <TableHeaderCell>Actions</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {files.map((file, index) => (
              <TableRow key={file.path}>
                {!isSingleFileMode ? (
                  <TableCell className="font-mono text-xs text-muted">
                    #{index + 1}
                  </TableCell>
                ) : null}
                <TableCell>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="break-all font-mono text-sm font-semibold">
                        {file.path}
                      </span>
                      <CopyPathButton path={file.path} />
                    </div>
                    {file.reasons && file.reasons.length > 0 ? (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {file.reasons.map((reason) => (
                          <Badge className="normal-case font-medium text-[11px]" key={reason} tone="warning">
                            {formatTitleCase(reason)}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">
                  {(file.risk_score * 100).toFixed(1)}%
                </TableCell>
                <TableCell>
                  <ComponentDetails components={file.components} />
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    <Button asChild size="sm" variant="ghost">
                      <Link
                        href={`/repositories/${repositoryId}/impact?path=${encodeURIComponent(file.path)}`}
                      >
                        <Zap aria-hidden="true" className="size-3.5" />
                        Impact
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link
                        href={`/repositories/${repositoryId}/graph?path=${encodeURIComponent(file.path)}`}
                      >
                        <GitGraph aria-hidden="true" className="size-3.5" />
                        Graph
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="ghost">
                      <Link
                        href={`/repositories/${repositoryId}/tests?path=${encodeURIComponent(file.path)}`}
                      >
                        <FlaskConical aria-hidden="true" className="size-3.5" />
                        Tests
                      </Link>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

const COMPONENT_DESCRIPTIONS: Record<string, { desc: string; label: string }> = {
  fan_in: {
    label: "Fan In",
    desc: "Number of incoming dependencies (other modules that import this file). High fan-in indicates wide impact if modified.",
  },
  fan_out: {
    label: "Fan Out",
    desc: "Number of outgoing dependencies (modules imported by this file). High fan-out makes this file sensitive to external changes.",
  },
  centrality: {
    label: "Centrality",
    desc: "Graph centrality score measuring how critical this node is as an architectural hub connecting multiple components.",
  },
  complexity: {
    label: "Complexity",
    desc: "Cyclomatic decision pathway complexity. Highly complex control flows are prone to subtle bugs.",
  },
  churn: {
    label: "Churn",
    desc: "Recent file modification frequency. Frequently edited files have a higher likelihood of regression.",
  },
  dependency: {
    label: "Dependency",
    desc: "Structural coupling strength in the repository dependency graph.",
  },
  risk: {
    label: "Risk",
    desc: "Overall heuristic risk score combining structural metrics and churn history.",
  },
  file_size: {
    label: "File Size",
    desc: "Relative line count and volume of source code in this file.",
  },
  bugfix_frequency: {
    label: "Bugfix Frequency",
    desc: "Historical frequency of commit messages referencing bug fixes in this file.",
  },
  test_coverage_proxy: {
    label: "Test Coverage Proxy",
    desc: "Estimated structural test coverage derived from linked unit tests and spec files.",
  },
};

function ComponentDetails({ components }: { components: Record<string, number> }) {
  const entries = Object.entries(components).sort((left, right) => right[1] - left[1]);

  if (entries.length === 0) {
    return <span className="text-sm text-muted">No components</span>;
  }

  return (
    <div className="min-w-44 space-y-2">
      {entries.map(([name, value]) => {
        const info = COMPONENT_DESCRIPTIONS[name] || {
          label: formatTitleCase(formatSnakeCase(name)),
          desc: `Architectural signal weight for ${formatTitleCase(formatSnakeCase(name))}.`,
        };

        return (
          <div className="space-y-1" key={name}>
            <div className="flex justify-between gap-3 text-xs">
              <TermTooltip description={info.desc} term={info.label} />
              <span className="font-mono">{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 w-full rounded-sm bg-background border border-border/80 dark:bg-slate-950 dark:border-slate-700/80 overflow-hidden shadow-inner">
              <div
                className="h-full bg-primary"
                style={{ width: `${Math.min(100, Math.max(0, value) * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Metric({
  description,
  label,
  value,
}: {
  description?: string;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border bg-panel-muted px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {description ? <TermTooltip description={description} term={label} /> : label}
      </div>
      <div className="mt-1 font-mono text-lg font-semibold">{value}</div>
    </div>
  );
}

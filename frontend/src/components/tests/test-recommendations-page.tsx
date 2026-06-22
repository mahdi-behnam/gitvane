"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { ClipboardList, FlaskConical, Link2, Send } from "lucide-react";
import { FormEvent, useEffect, useId, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { ChangedFileInput, TestRecommendation } from "@/lib/api/types";
import {
  useGetRepositoryQuery,
  useRecommendTestsMutation,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

function parseChangedFiles(value: string): ChangedFileInput[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((path) => ({
      path,
    }));
}

function parseImpactedFiles(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function TestRecommendationsPage({ repositoryId }: { repositoryId: number }) {
  const validRepositoryId = Number.isFinite(repositoryId) ? repositoryId : null;
  const formId = useId();
  const [changedFiles, setChangedFiles] = useState(
    "backend/app/services/indexing_service.py",
  );
  const [impactedFiles, setImpactedFiles] = useState("");
  const [topK, setTopK] = useState(10);
  const [clientError, setClientError] = useState<string | null>(null);
  const [recommendTests, recommendationState] = useRecommendTestsMutation();
  const repository = useGetRepositoryQuery(validRepositoryId ?? skipToken);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (validRepositoryId) {
      dispatch(setActiveRepositoryId(validRepositoryId));
    }
  }, [dispatch, validRepositoryId]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validRepositoryId) {
      setClientError("The repository identifier in the route is not valid.");
      return;
    }

    const parsedChangedFiles = parseChangedFiles(changedFiles);
    if (parsedChangedFiles.length === 0) {
      setClientError("Enter at least one changed file path.");
      return;
    }

    const parsedImpactedFiles = parseImpactedFiles(impactedFiles);
    setClientError(null);

    await recommendTests({
      changed_files: parsedChangedFiles,
      impacted_files: parsedImpactedFiles.length > 0 ? parsedImpactedFiles : undefined,
      repository_id: validRepositoryId,
      top_k: topK,
    });
  };

  const apiError = recommendationState.error
    ? normalizeApiError(recommendationState.error).message
    : null;
  const error = clientError ?? apiError;
  const recommendations = recommendationState.data?.recommended_tests ?? [];

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
          <Badge tone="info">Tests</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">
            Test recommendations
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Recommend likely relevant tests from changed files and optional impacted
            files. Tests are not executed from this screen.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <h2 className="text-sm font-semibold">Recommendation inputs</h2>
            <Badge tone="warning">Does not run tests</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                <label
                  className="block text-sm font-medium"
                  htmlFor={`${formId}-changed-files`}
                >
                  Changed files
                </label>
                <Textarea
                  id={`${formId}-changed-files`}
                  onChange={(event) => {
                    setChangedFiles(event.target.value);
                    setClientError(null);
                  }}
                  placeholder="backend/app/services/indexing_service.py"
                  value={changedFiles}
                />
                <p className="text-xs leading-5 text-muted">
                  One file path per line. These are the direct changes.
                </p>
              </div>
              <div className="space-y-2">
                <label
                  className="block text-sm font-medium"
                  htmlFor={`${formId}-impacted-files`}
                >
                  Impacted files
                </label>
                <Textarea
                  id={`${formId}-impacted-files`}
                  onChange={(event) => setImpactedFiles(event.target.value)}
                  placeholder="backend/app/api/v1/endpoints/indexing.py"
                  value={impactedFiles}
                />
                <p className="text-xs leading-5 text-muted">
                  Optional. Include likely affected files from impact analysis.
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="w-full space-y-2 md:w-40">
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
              <Button
                disabled={recommendationState.isLoading}
                type="submit"
                variant="primary"
              >
                <Send aria-hidden="true" className="size-4" />
                {recommendationState.isLoading ? "Recommending" : "Recommend tests"}
              </Button>
            </div>
          </form>

          {error ? (
            <p className="mt-4 rounded-md border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {recommendationState.isLoading ? (
        <RecommendationLoadingState />
      ) : recommendationState.isSuccess && recommendations.length === 0 ? (
        <EmptyState
          description="The backend did not return any recommended tests for these files."
          icon={<FlaskConical aria-hidden="true" className="size-5" />}
          title="No recommendations"
        />
      ) : recommendations.length > 0 ? (
        <RecommendationResults recommendations={recommendations} />
      ) : (
        <EmptyState
          description="Enter changed files to ask RepoLens which tests are likely relevant."
          icon={<ClipboardList aria-hidden="true" className="size-5" />}
          title="Ready to recommend tests"
        />
      )}
    </div>
  );
}

function RecommendationLoadingState() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }, (_, index) => (
        <Card className="p-5" key={index}>
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="mt-4 h-4 w-32" />
          <Skeleton className="mt-4 h-16 w-full" />
        </Card>
      ))}
    </div>
  );
}

function RecommendationResults({
  recommendations,
}: {
  recommendations: TestRecommendation[];
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Recommended tests</h2>
          <p className="mt-1 text-xs text-muted">
            Review these candidates in your normal test runner; this page does not
            execute tests.
          </p>
        </div>
        <Badge>{recommendations.length} returned</Badge>
      </div>
      <div className="grid gap-3">
        {recommendations.map((recommendation, index) => (
          <RecommendationCard
            index={index}
            key={`${recommendation.path}:${index}`}
            recommendation={recommendation}
          />
        ))}
      </div>
    </section>
  );
}

function RecommendationCard({
  index,
  recommendation,
}: {
  index: number;
  recommendation: TestRecommendation;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="info">#{index + 1}</Badge>
              <h3 className="min-w-0 break-all font-mono text-sm font-semibold">
                {recommendation.path}
              </h3>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted">
              {recommendation.reason ?? "No reason returned by the backend."}
            </p>
          </div>
          <Metric label="Score" value={recommendation.score.toFixed(3)} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Link2 aria-hidden="true" className="size-4 text-muted" />
            Linked files
          </div>
          {recommendation.linked_files.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {recommendation.linked_files.map((file) => (
                <span
                  className="rounded-md border border-border bg-panel-muted px-2 py-1 font-mono text-xs text-muted"
                  key={file}
                >
                  {file}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">No linked files returned.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="w-fit rounded-md border border-border bg-panel-muted px-3 py-2 text-right">
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
        {label}
      </div>
      <div className="mt-1 font-mono text-sm font-semibold">{value}</div>
    </div>
  );
}

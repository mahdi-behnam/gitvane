"use client";

import { ArrowRight, GitGraph, Search } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useId, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { SemanticSearchResult } from "@/lib/api/types";
import {
  useGetRepositoryQuery,
  useSemanticSearchMutation,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";
import { skipToken } from "@reduxjs/toolkit/query";

export function SemanticSearchPage({ repositoryId }: { repositoryId: number }) {
  const validRepositoryId = Number.isFinite(repositoryId) ? repositoryId : null;
  const formId = useId();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);
  const [clientError, setClientError] = useState<string | null>(null);
  const [semanticSearch, searchState] = useSemanticSearchMutation();
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

    if (!query.trim()) {
      setClientError("Enter a semantic search query.");
      return;
    }

    setClientError(null);
    await semanticSearch({
      query: query.trim(),
      repository_id: validRepositoryId,
      top_k: topK,
    });
  };

  const apiError = searchState.error
    ? normalizeApiError(searchState.error).message
    : null;
  const error = clientError ?? apiError;
  const results = searchState.data?.results ?? [];

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
          <Badge tone="info">Search</Badge>
          <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Semantic search</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Search indexed code by intent and inspect scored snippets from the selected
            repository.
          </p>
        </div>
        <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
          {repository.data?.name ?? `Repository ${validRepositoryId}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold">Query</h2>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 lg:grid-cols-[1fr_140px_auto]"
            onSubmit={handleSubmit}
          >
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor={`${formId}-query`}>
                Search query
              </label>
              <Input
                id={`${formId}-query`}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setClientError(null);
                }}
                placeholder="Where is repository indexing triggered?"
                value={query}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium" htmlFor={`${formId}-top-k`}>
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
            <div className="flex items-end">
              <Button disabled={searchState.isLoading} type="submit" variant="primary">
                <Search aria-hidden="true" className="size-4" />
                {searchState.isLoading ? "Searching" : "Search"}
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

      {searchState.isLoading ? (
        <SearchLoadingState />
      ) : searchState.isSuccess && results.length === 0 ? (
        <EmptyState
          description="No indexed snippets matched this query. Try a different concept or increase the result count."
          icon={<Search aria-hidden="true" className="size-5" />}
          title="No matching snippets"
        />
      ) : results.length > 0 ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Results</h2>
            <Badge>{results.length} returned</Badge>
          </div>
          {results.map((result, index) => (
            <SearchResultCard
              key={`${result.path}:${result.start_line}:${index}`}
              repositoryId={validRepositoryId}
              result={result}
            />
          ))}
        </section>
      ) : (
        <EmptyState
          description="Enter a query to search indexed files by semantic meaning."
          icon={<Search aria-hidden="true" className="size-5" />}
          title="Search indexed code"
        />
      )}
    </div>
  );
}

function SearchLoadingState() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }, (_, index) => (
        <Card className="p-5" key={index}>
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="mt-4 h-20 w-full" />
          <Skeleton className="mt-4 h-4 w-40" />
        </Card>
      ))}
    </div>
  );
}

function SearchResultCard({
  repositoryId,
  result,
}: {
  repositoryId: number;
  result: SemanticSearchResult;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h3 className="truncate font-mono text-sm font-semibold">{result.path}</h3>
            <p className="mt-1 font-mono text-xs text-muted">
              {result.symbol ?? "File scope"} · lines {result.start_line}-
              {result.end_line}
            </p>
          </div>
          <Badge tone="info">{result.score.toFixed(3)}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <pre className="overflow-x-auto rounded-md border border-border bg-panel-muted p-4 font-mono text-xs leading-6 text-foreground">
          <code>{result.snippet}</code>
        </pre>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link href={`/repositories/${repositoryId}/graph`}>
              <GitGraph aria-hidden="true" className="size-4" />
              Open graph
            </Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link href={`/repositories/${repositoryId}/impact`}>
              Send to impact
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

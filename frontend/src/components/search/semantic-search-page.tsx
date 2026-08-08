"use client";

import { skipToken } from "@reduxjs/toolkit/query";
import { AlertCircle, ArrowRight, FlaskConical, GitGraph, RefreshCw, Search, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeApiError } from "@/lib/api/errors";
import type { SemanticSearchResult } from "@/lib/api/types";
import { formatPercent } from "@/lib/format";
import {
  useGetRepositoryQuery,
  useSemanticSearchMutation,
} from "@/store/api/repolensApi";
import { useAppDispatch } from "@/store/hooks";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";

import { CodeHighlight } from "@/components/ui/code-highlight";

export function SemanticSearchPage({
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
  const [query, setQuery] = useState(pathParam);
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

  useEffect(() => {
    if (pathParam) {
      setQuery(pathParam);
    }
  }, [pathParam]);

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
                placeholder="e.g. How are authentication tokens validated?"
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
            <Notice className="mt-4" tone="danger">
              {error}
            </Notice>
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
            <span className="text-xs text-muted font-medium">{results.length} returned</span>
          </div>
          {results.map((result) => (
            <SearchResultCard
              key={`${result.path}:${result.start_line}:${result.end_line}`}
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
        <Card className="p-5" key={`search-skeleton-${index}`}>
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="mt-4 h-20 w-full" />
          <Skeleton className="mt-4 h-4 w-40" />
        </Card>
      ))}
    </div>
  );
}

function parseSearchResultMetadata(result: SemanticSearchResult) {
  let path = result.path;
  let language = result.language ?? null;
  let symbol = result.symbol ?? null;
  let signature = result.signature ?? null;
  let cleanSnippet = result.snippet;

  const lines = result.snippet.split("\n");
  if (
    lines.length > 0 &&
    (lines[0].startsWith("path:") ||
      lines[0].startsWith("language:") ||
      lines[0].startsWith("symbol:") ||
      lines[0].startsWith("signature:"))
  ) {
    let headerEndIdx = 0;
    while (headerEndIdx < lines.length && lines[headerEndIdx].trim() !== "") {
      const line = lines[headerEndIdx];
      if (line.startsWith("path:") && !path) {
        path = line.slice(5).trim();
      } else if (line.startsWith("language:") && !language) {
        language = line.slice(9).trim();
      } else if (line.startsWith("symbol:") && !symbol) {
        symbol = line.slice(7).trim();
      } else if (line.startsWith("signature:") && !signature) {
        signature = line.slice(10).trim();
      }
      headerEndIdx++;
    }
    if (headerEndIdx < lines.length) {
      cleanSnippet = lines.slice(headerEndIdx + 1).join("\n").trim();
    }
  }

  if (!language && path) {
    const ext = path.split(".").pop()?.toLowerCase();
    const extMap: Record<string, string> = {
      c: "c",
      cpp: "cpp",
      css: "css",
      go: "go",
      html: "html",
      java: "java",
      js: "javascript",
      json: "json",
      jsx: "javascript",
      md: "markdown",
      py: "python",
      rs: "rust",
      sh: "bash",
      sql: "sql",
      ts: "typescript",
      tsx: "typescript",
      yaml: "yaml",
      yml: "yaml",
    };
    if (ext && extMap[ext]) {
      language = extMap[ext];
    }
  }

  return {
    code: cleanSnippet,
    language,
    path,
    signature,
    symbol,
  };
}

function SearchResultCard({
  repositoryId,
  result,
}: {
  repositoryId: string;
  result: SemanticSearchResult;
}) {
  const { path, language, symbol, signature, code } = parseSearchResultMetadata(result);

  return (
    <Card>
      <CardHeader>
        <div className="space-y-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
              <span className="font-semibold text-foreground">{path}</span>
              <span className="text-muted">·</span>
              <span className="rounded border border-border bg-panel-muted px-1.5 py-0.5 text-muted">
                lines {result.start_line}-{result.end_line}
              </span>
              {language ? <span className="font-mono text-xs text-muted font-medium">{language}</span> : null}
              {symbol ? (
                <span className="rounded border border-border bg-panel-muted px-1.5 py-0.5 font-medium text-foreground">
                  {symbol}
                </span>
              ) : null}
            </div>
            <span className="font-mono text-xs font-semibold text-primary">{formatPercent(result.score)}</span>
          </div>

          {signature ? (
            <div className="flex items-center gap-2 rounded border border-border/80 bg-panel-muted/50 p-2 text-xs">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                Signature:
              </span>
              <CodeHighlight code={signature} inline language={language} />
            </div>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        <CodeHighlight code={code} language={language} />
        <div className="mt-4 flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link href={`/repositories/${repositoryId}/graph?path=${encodeURIComponent(path)}`}>
              <GitGraph aria-hidden="true" className="size-4" />
              Open graph
            </Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link href={`/repositories/${repositoryId}/impact?path=${encodeURIComponent(path)}`}>
              Send to impact
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link href={`/repositories/${repositoryId}/risk?path=${encodeURIComponent(path)}`}>
              <ShieldAlert aria-hidden="true" className="size-4" />
              View risk
            </Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link href={`/repositories/${repositoryId}/tests?path=${encodeURIComponent(path)}`}>
              <FlaskConical aria-hidden="true" className="size-4" />
              Recommend tests
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}


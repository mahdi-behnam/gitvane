"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import Link from "next/link";
import { AddRepositoryDialog } from "@/components/repositories/add-repository-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
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
import { formatDateTime } from "@/lib/format";
import { useListRepositoriesQuery } from "@/store/api/repolensApi";

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

export function RepositoryManagementPage() {
  const repositories = useListRepositoriesQuery();
  const apiError = repositories.error
    ? normalizeApiError(repositories.error).message
    : null;

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
                        description="Add a repository with a clone URL or local path to start indexing code."
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
                          {repository.local_path ?? repository.clone_url ?? "No source"}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        tone={repository.status === "indexed" ? "success" : "neutral"}
                      >
                        {repository.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted">
                      {repository.default_branch ?? repository.current_ref ?? "Unknown"}
                    </TableCell>
                    <TableCell className="text-muted">
                      {formatDateTime(repository.indexed_at)}
                    </TableCell>
                    <TableCell>
                      <Button asChild size="sm">
                        <Link href={`/repositories/${repository.id}`}>View</Link>
                      </Button>
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

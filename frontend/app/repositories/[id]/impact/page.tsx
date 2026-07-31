import { ImpactAnalysisPage } from "@/components/impact/impact-analysis-page";
import { Suspense } from "react";

export default async function RepositoryImpactPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { id } = await params;
  const { path, search, query } = (await searchParams) || {};
  const initialPath =
    typeof path === "string"
      ? path
      : typeof search === "string"
        ? search
        : typeof query === "string"
          ? query
          : undefined;

  return (
    <Suspense fallback={null}>
      <ImpactAnalysisPage initialPath={initialPath} repositoryId={id} />
    </Suspense>
  );
}

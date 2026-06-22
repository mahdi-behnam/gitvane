import { ImpactAnalysisPage } from "@/components/impact/impact-analysis-page";

export default async function RepositoryImpactPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <ImpactAnalysisPage repositoryId={Number(id)} />;
}

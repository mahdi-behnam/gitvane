import { GraphExplorerPage } from "@/components/graph/graph-explorer-page";

export default async function RepositoryGraphPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <GraphExplorerPage repositoryId={id} />;
}

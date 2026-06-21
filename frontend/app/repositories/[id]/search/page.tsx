import { SemanticSearchPage } from "@/components/search/semantic-search-page";

export default async function RepositorySearchPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <SemanticSearchPage repositoryId={Number(id)} />;
}

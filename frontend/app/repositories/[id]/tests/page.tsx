import { TestRecommendationsPage } from "@/components/tests/test-recommendations-page";

export default async function RepositoryTestsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <TestRecommendationsPage repositoryId={id} />;
}

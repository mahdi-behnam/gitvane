import { RepositoryDetailPage } from "@/components/repositories/repository-detail-page";

export default async function RepositoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <RepositoryDetailPage repositoryId={Number(id)} />;
}

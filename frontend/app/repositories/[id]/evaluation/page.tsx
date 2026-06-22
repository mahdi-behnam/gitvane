import { EvaluationDashboardPage } from "@/components/evaluation/evaluation-dashboard-page";

export default async function RepositoryEvaluationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <EvaluationDashboardPage repositoryId={Number(id)} />;
}

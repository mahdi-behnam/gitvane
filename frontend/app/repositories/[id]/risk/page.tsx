import { RiskDashboardPage } from "@/components/risk/risk-dashboard-page";

export default async function RepositoryRiskPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return <RiskDashboardPage repositoryId={id} />;
}

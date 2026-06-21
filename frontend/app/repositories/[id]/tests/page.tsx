import { SectionPage } from "@/components/app/section-page";

export default function RepositoryTestsPage() {
  return (
    <SectionPage
      description="Test recommendations for this repository will list likely relevant tests without executing them."
      label="Tests"
      title="Test recommendations"
    />
  );
}

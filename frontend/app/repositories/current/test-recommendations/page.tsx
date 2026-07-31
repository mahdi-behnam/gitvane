import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function TestRecommendationsCurrentPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Select a repository to view test recommendations."
      label="Tests"
      title="Test Recommendations"
    />
  );
}

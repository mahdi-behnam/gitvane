import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function TestsPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Recommended tests will be listed for changed and likely impacted files."
      label="Tests"
      title="Test recommendations"
    />
  );
}

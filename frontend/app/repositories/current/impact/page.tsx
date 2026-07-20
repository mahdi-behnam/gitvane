import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function ImpactPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Impact analysis will accept changed files, raw diffs, or base and head refs."
      label="Impact"
      title="Impact analysis"
    />
  );
}

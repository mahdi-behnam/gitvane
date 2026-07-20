import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function RiskPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Risk ranking will show file-level heuristic scores and supporting components."
      label="Risk"
      title="Risk ranking"
    />
  );
}

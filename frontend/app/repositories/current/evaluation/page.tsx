import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function EvaluationPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Evaluation runs, metrics, baseline comparisons, and Markdown reports will appear here."
      label="Evaluation"
      title="Evaluation"
    />
  );
}

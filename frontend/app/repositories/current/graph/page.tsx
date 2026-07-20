import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function GraphPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Repository graph data will render here after graph endpoints are wired."
      label="Graph"
      title="Dependency graph"
    />
  );
}

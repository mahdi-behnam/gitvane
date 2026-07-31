import Link from "next/link";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";

export default function FilesPage() {
  return (
    <SectionPage
      action={
        <Button asChild variant="primary">
          <Link href="/repositories">Select repository</Link>
        </Button>
      }
      description="Select a repository to search indexed code files."
      label="Files"
      title="Code Search & Files"
    />
  );
}

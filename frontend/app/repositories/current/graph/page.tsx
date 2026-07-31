"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";
import { useAppSelector } from "@/store/hooks";

export default function CurrentGraphPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeRepositoryId = useAppSelector(
    (state) => state.repositorySelection.activeRepositoryId
  );

  useEffect(() => {
    if (activeRepositoryId) {
      const queryString = searchParams?.toString();
      const target = `/repositories/${activeRepositoryId}/graph${queryString ? `?${queryString}` : ""}`;
      router.replace(target);
    }
  }, [activeRepositoryId, router, searchParams]);

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

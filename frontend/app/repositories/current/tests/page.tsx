"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { SectionPage } from "@/components/app/section-page";
import { Button } from "@/components/ui/button";
import { useAppSelector } from "@/store/hooks";

export default function CurrentTestsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeRepositoryId = useAppSelector(
    (state) => state.repositorySelection.activeRepositoryId
  );

  useEffect(() => {
    if (activeRepositoryId) {
      const queryString = searchParams?.toString();
      const target = `/repositories/${activeRepositoryId}/tests${queryString ? `?${queryString}` : ""}`;
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
      description="Recommended tests will be listed for changed and likely impacted files."
      label="Tests"
      title="Test recommendations"
    />
  );
}

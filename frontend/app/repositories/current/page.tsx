"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector } from "@/store/hooks";
import { useListRepositoriesQuery } from "@/store/api/repolensApi";

export default function CurrentRepositoryIndexPage() {
  const router = useRouter();
  const activeRepositoryId = useAppSelector(
    (state) => state.repositorySelection.activeRepositoryId
  );
  const { data: repositories, isLoading } = useListRepositoriesQuery();

  useEffect(() => {
    if (isLoading) return;

    if (activeRepositoryId) {
      router.replace(`/repositories/${activeRepositoryId}`);
      return;
    }

    if (repositories && repositories.length > 0) {
      router.replace(`/repositories/${repositories[0].id}`);
      return;
    }

    router.replace("/repositories");
  }, [activeRepositoryId, repositories, isLoading, router]);

  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center p-8 text-center">
      <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent mb-3" />
      <p className="text-xs text-muted font-mono">Resolving active repository...</p>
    </div>
  );
}

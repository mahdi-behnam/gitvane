import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";

type SectionPageProps = {
  action?: ReactNode;
  description: string;
  label?: string;
  title: string;
};

export function SectionPage({ action, description, label, title }: SectionPageProps) {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="border-b border-border pb-6">
        {label ? <Badge tone="info">{label}</Badge> : null}
        <h1 className="mt-3 text-3xl font-semibold md:text-4xl">{title}</h1>
      </div>
      <EmptyState action={action} description={description} title={title} />
    </div>
  );
}

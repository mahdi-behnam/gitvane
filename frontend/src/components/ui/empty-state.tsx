import type { HTMLAttributes, ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type EmptyStateProps = HTMLAttributes<HTMLDivElement> & {
  action?: ReactNode;
  description: string;
  icon?: ReactNode;
  title: string;
};

export function EmptyState({
  action,
  className,
  description,
  icon,
  title,
  ...props
}: EmptyStateProps) {
  return (
    <Card
      className={cn(
        "flex min-h-56 flex-col items-start justify-center p-8 md:p-10",
        className,
      )}
      {...props}
    >
      {icon ? (
        <div className="mb-5 grid size-11 place-items-center rounded-lg border border-border bg-panel-muted text-primary">
          {icon}
        </div>
      ) : null}
      <div className="max-w-2xl">
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      </div>
      {action ? <div className="mt-5 flex flex-wrap gap-2">{action}</div> : null}
    </Card>
  );
}

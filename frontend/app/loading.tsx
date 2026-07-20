import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Header Section */}
      <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div className="space-y-3">
          {/* Badge Skeleton */}
          <Skeleton className="h-5 w-20 rounded" />
          {/* Title Skeleton */}
          <Skeleton className="h-9 w-64 md:h-10" />
          {/* Subtitle Skeleton */}
          <Skeleton className="h-4 w-[280px] sm:w-[450px]" />
        </div>
        {/* Action Button Skeleton */}
        <Skeleton className="h-10 w-32 shrink-0" />
      </div>

      {/* Metric Cards Row */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-lg border border-border bg-panel p-4 space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-6 w-24" />
          </div>
        ))}
      </div>

      {/* Main Content Area: 3 Block Cards */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Large Main Card (2/3 width on desktop) */}
        <div className="rounded-lg border border-border bg-panel lg:col-span-2">
          <div className="border-b border-border p-5">
            <Skeleton className="h-5 w-40" />
          </div>
          <div className="p-5 space-y-4">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-3 w-1/4" />
              </div>
            </div>
            <div className="space-y-2 pt-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </div>
        </div>

        {/* Sidebar Cards Area (1/3 width on desktop) */}
        <div className="space-y-6">
          {/* Sidebar Card 1 */}
          <div className="rounded-lg border border-border bg-panel">
            <div className="border-b border-border p-5">
              <Skeleton className="h-5 w-32" />
            </div>
            <div className="p-5 space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          </div>

          {/* Sidebar Card 2 */}
          <div className="rounded-lg border border-border bg-panel">
            <div className="border-b border-border p-5">
              <Skeleton className="h-5 w-36" />
            </div>
            <div className="p-5 space-y-3">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

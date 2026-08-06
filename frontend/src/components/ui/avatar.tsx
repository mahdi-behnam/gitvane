"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface AvatarProps {
  alt?: string;
  className?: string;
  fallback?: string;
  hue?: number;
  src?: string | null;
}

export function Avatar({
  alt = "User avatar",
  className,
  fallback = "GU",
  hue = 0,
  src,
}: AvatarProps) {
  const [imageError, setImageError] = useState(false);

  if (src && !imageError) {
    return (
      <img
        alt={alt}
        className={cn(
          "size-9 shrink-0 rounded-xl object-cover shadow-sm ring-2 ring-panel",
          className,
        )}
        onError={() => setImageError(true)}
        src={src}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-white shadow-sm ring-2 ring-panel",
        className,
      )}
      style={{ backgroundColor: `hsl(${hue}, 40%, 42%)` }}
    >
      {fallback}
    </div>
  );
}

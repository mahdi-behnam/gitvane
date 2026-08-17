"use client";

import * as React from "react";
import { useSearchRepositoryRefsQuery } from "@/store/api/gitvaneApi";
import { Selector, SelectorOption, SelectorProps } from "./selector";

export type RefSelectorProps = Omit<SelectorProps, "options"> & {
  options?: SelectorOption[];
  refType?: "branch" | "tag" | "commit";
  repositoryId?: string;
};

export function RefSelector({
  allowCustomValue = true,
  disabled,
  loading,
  options: externalOptions,
  placeholder = "Select branch, tag, or commit...",
  refType,
  repositoryId,
  value,
  ...props
}: RefSelectorProps) {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");

  // Debounce search query by 200ms
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data: refs = [], isFetching } = useSearchRepositoryRefsQuery(
    {
      limit: 50,
      query: debouncedQuery,
      ref_type: refType,
      repositoryId: repositoryId!,
    },
    { skip: !repositoryId },
  );

  const options: SelectorOption[] = React.useMemo(() => {
    const list: SelectorOption[] = externalOptions
      ? [...externalOptions]
      : refs.map((ref) => {
          let badgeTone: "info" | "success" | "warning" | "danger" | "muted" = "info";
          if (ref.ref_type === "tag") badgeTone = "success";
          else if (ref.ref_type === "commit") badgeTone = "muted";

          return {
            badge: ref.ref_type,
            badgeTone,
            description: ref.commit_message || (ref.commit_sha ? `Commit ${ref.commit_sha}` : undefined),
            label: ref.name,
            value: ref.name,
          };
        });

    // If current value is not in returned list, append it so selected value is displayed
    const currentValues = Array.isArray(value)
      ? value
      : typeof value === "string" && value !== ""
        ? value.split(",").map((s) => s.trim()).filter(Boolean)
        : [];

    for (const val of currentValues) {
      if (val && !list.some((o) => o.value === val)) {
        list.unshift({
          badge: "ref",
          badgeTone: "muted",
          description: "Current selection",
          label: val,
          value: val,
        });
      }
    }

    return list;
  }, [externalOptions, refs, value]);

  return (
    <Selector
      {...props}
      allowCustomValue={allowCustomValue}
      disabled={disabled}
      emptyText="No matching refs found."
      loading={loading ?? isFetching}
      onSearchChange={(q) => setSearchQuery(q)}
      options={options}
      placeholder={placeholder}
      searchPlaceholder="Type branch, tag, or commit..."
      value={value}
    />
  );
}

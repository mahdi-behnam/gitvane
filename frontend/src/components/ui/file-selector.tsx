"use client";

import * as React from "react";
import { useSearchRepositoryFilesQuery } from "@/store/api/gitvaneApi";
import { Selector, SelectorOption, SelectorProps } from "./selector";

export type FileSelectorProps = Omit<SelectorProps, "options"> & {
  language?: string;
  repositoryId: string;
};

export function FileSelector({
  disabled,
  language,
  placeholder = "Select or search file...",
  repositoryId,
  value,
  ...props
}: FileSelectorProps) {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");

  // Debounce search query by 200ms
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data: files = [], isFetching } = useSearchRepositoryFilesQuery(
    {
      language: language || undefined,
      limit: 50,
      query: debouncedQuery,
      repositoryId,
    },
    { skip: !repositoryId },
  );

  const options: SelectorOption[] = React.useMemo(() => {
    const list: SelectorOption[] = files.map((file) => ({
      badge: `${file.loc} LOC`,
      description: `${file.language}${file.is_test ? " • test" : ""}`,
      label: file.path,
      value: file.path,
    }));

    // If current value is not in returned list, append it so selected value is displayed
    const currentValues = Array.isArray(value)
      ? value
      : typeof value === "string" && value !== ""
        ? value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean)
        : [];

    for (const val of currentValues) {
      if (val && !list.some((o) => o.value === val)) {
        list.unshift({
          description: "Selected path",
          label: val,
          value: val,
        });
      }
    }

    return list;
  }, [files, value]);

  return (
    <div className="space-y-1 w-full">
      <Selector
        {...props}
        allowCustomValue
        disabled={disabled}
        emptyText="No matching files found."
        loading={isFetching}
        onSearchChange={(q) => setSearchQuery(q)}
        options={options}
        placeholder={placeholder}
        searchPlaceholder="Type file path..."
        value={value}
      />
      {language ? (
        <div className="flex items-center gap-1.5 text-[11px] text-muted">
          <span>Filtered by language:</span>
          <span className="rounded bg-panel-muted border border-border px-1.5 py-0.5 font-mono font-medium text-foreground">
            {language}
          </span>
        </div>
      ) : null}
    </div>
  );
}

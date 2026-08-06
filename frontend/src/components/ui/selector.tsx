"use client";

import * as React from "react";
import { Check, ChevronDown, Loader2, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type SelectorOption = {
  badge?: string;
  badgeTone?: "info" | "success" | "warning" | "danger" | "muted";
  description?: string;
  label: string;
  value: string;
};

export type SelectorProps = {
  allowCustomValue?: boolean;
  className?: string;
  disabled?: boolean;
  emptyText?: string;
  id?: string;
  loading?: boolean;
  mode?: "single" | "multi";
  onChange?: (value: string | string[]) => void;
  onOpenChange?: (open: boolean) => void;
  onSearchChange?: (query: string) => void;
  options: SelectorOption[];
  placeholder?: string;
  refetchOnOpen?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  value?: string | string[];
};

export function Selector({
  allowCustomValue = false,
  className,
  disabled = false,
  emptyText = "No matching options found.",
  id,
  loading = false,
  mode = "single",
  onChange,
  onOpenChange,
  onSearchChange,
  options = [],
  placeholder = "Select an option...",
  searchable = true,
  searchPlaceholder = "Type to search...",
  value,
}: SelectorProps) {

  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Close on click outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        onOpenChange?.(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onOpenChange]);

  const handleToggleOpen = () => {
    if (disabled) return;
    const nextOpen = !open;
    setOpen(nextOpen);
    onOpenChange?.(nextOpen);
    if (nextOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const filteredOptions = React.useMemo(() => {
    if (onSearchChange) return options;
    if (!search.trim()) return options;
    const query = search.toLowerCase().trim();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(query) ||
        opt.value.toLowerCase().includes(query) ||
        (opt.description && opt.description.toLowerCase().includes(query)),
    );
  }, [options, search, onSearchChange]);

  const selectedValues = React.useMemo(() => {
    if (Array.isArray(value)) return value;
    if (typeof value === "string" && value !== "") {
      return mode === "multi" ? value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean) : [value];
    }
    return [];
  }, [value, mode]);

  const handleSelectOption = (optValue: string) => {
    if (mode === "single") {
      onChange?.(optValue);
      setOpen(false);
      onOpenChange?.(false);
    } else {
      const exists = selectedValues.includes(optValue);
      const nextValues = exists
        ? selectedValues.filter((v) => v !== optValue)
        : [...selectedValues, optValue];
      onChange?.(nextValues);
    }
  };

  const handleRemoveChip = (optValue: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (mode === "multi") {
      const nextValues = selectedValues.filter((v) => v !== optValue);
      onChange?.(nextValues);
    } else {
      onChange?.("");
    }
  };

  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setSearch(q);
    if (onSearchChange) {
      onSearchChange(q);
    }
  };

  const getOptionLabel = (val: string) => {
    const match = options.find((o) => o.value === val);
    return match ? match.label : val;
  };

  return (
    <div className={cn("relative w-full", className)} ref={containerRef}>
      {/* Trigger Button */}
      <button
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-labelledby={id ? `${id}-label` : undefined}
        className={cn(
          "flex min-h-9 w-full items-center justify-between gap-2 rounded-md border border-border bg-panel px-3 py-1.5 text-left text-sm text-foreground shadow-none transition-colors",
          "focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
          disabled && "cursor-not-allowed opacity-50",
          open && "border-primary ring-2 ring-primary/20",
        )}
        aria-controls={open ? `${id || "selector"}-listbox` : undefined}
        disabled={disabled}
        id={id}
        onClick={handleToggleOpen}
        role="combobox"
        type="button"
      >

        <div className="flex flex-wrap items-center gap-1.5 overflow-hidden py-0.5">
          {selectedValues.length === 0 ? (
            <span className="truncate text-muted">{placeholder}</span>
          ) : mode === "single" ? (
            <span className="truncate font-medium">{getOptionLabel(selectedValues[0])}</span>
          ) : (
            selectedValues.map((val) => (
              <span
                className="inline-flex items-center gap-1 rounded border border-border bg-panel-muted px-2 py-0.5 font-mono text-xs text-foreground"
                key={val}
              >
                <span className="max-w-44 truncate">{getOptionLabel(val)}</span>
                <span
                  className="rounded p-0.5 text-muted hover:bg-muted/20 hover:text-foreground"
                  onClick={(e) => handleRemoveChip(val, e)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      handleRemoveChip(val, e as unknown as React.MouseEvent);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <X className="size-3" />
                </span>
              </span>
            ))
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1 text-muted">
          {loading ? <Loader2 className="size-3.5 animate-spin" /> : null}
          <ChevronDown className={cn("size-4 transition-transform duration-200", open && "rotate-180")} />
        </div>
      </button>

      {/* Dropdown Popover */}
      {open ? (
        <div className="absolute z-50 mt-1 max-h-72 w-full overflow-hidden rounded-md border border-border bg-panel shadow-lg animate-in fade-in-50 zoom-in-95">
          {/* Search Box */}
          {searchable ? (
            <div className="flex items-center border-b border-border px-3 py-2">
              <Search className="mr-2 size-4 shrink-0 text-muted" />
              <input
                className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted"
                onChange={handleSearchInputChange}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && allowCustomValue && search.trim()) {
                    e.preventDefault();
                    handleSelectOption(search.trim());
                  }
                }}
                placeholder={searchPlaceholder}
                ref={inputRef}
                type="text"
                value={search}
              />
              {search ? (
                <button
                  className="text-muted hover:text-foreground"
                  onClick={() => {
                    setSearch("");
                    if (onSearchChange) onSearchChange("");
                  }}
                  type="button"
                >
                  <X className="size-3.5" />
                </button>
              ) : null}
            </div>
          ) : null}

          {/* Options List */}
          <div className="max-h-56 overflow-y-auto p-1 space-y-0.5">
            {loading && filteredOptions.length === 0 ? (
              <div className="flex items-center justify-center p-4 text-xs text-muted">
                <Loader2 className="mr-2 size-4 animate-spin" />
                Loading options...
              </div>
            ) : filteredOptions.length === 0 ? (
              <div className="p-3 text-center text-xs text-muted">
                {emptyText}
                {allowCustomValue && search.trim() ? (
                  <button
                    className="mt-2 block w-full rounded border border-dashed border-border py-1.5 text-xs text-primary hover:bg-panel-muted"
                    onClick={() => handleSelectOption(search.trim())}
                    type="button"
                  >
                    Use &quot;{search.trim()}&quot;
                  </button>
                ) : null}
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = selectedValues.includes(opt.value);

                return (
                  <button
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-xs transition-colors",
                      isSelected
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-foreground hover:bg-panel-muted",
                    )}
                    key={opt.value}
                    onClick={() => handleSelectOption(opt.value)}
                    type="button"
                  >
                    <div className="flex min-w-0 flex-col pr-2">
                      <span className="truncate font-mono text-xs">{opt.label}</span>
                      {opt.description ? (
                        <span className="mt-0.5 truncate text-[11px] font-normal text-muted">
                          {opt.description}
                        </span>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {opt.badge ? (
                        <span className="rounded border border-border bg-panel-muted px-1.5 py-0.5 font-mono text-[10px] text-muted">
                          {opt.badge}
                        </span>
                      ) : null}
                      {isSelected ? <Check className="size-3.5 text-primary" /> : null}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

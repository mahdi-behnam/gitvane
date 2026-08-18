export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not indexed";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


export function formatSnakeCase(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "0%";
  const pct = value * 100;
  return `${pct.toFixed(decimals)}%`;
}

export function formatTitleCase(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .trim()
    .replace(/\.$/, "")
    .split(" ")
    .map((word) =>
      word
        .split("-")
        .map((sub) => (sub ? sub.charAt(0).toUpperCase() + sub.slice(1) : ""))
        .join("-")
    )
    .join(" ");
}

/**
 * Resolves the user-facing branch/ref display string for a repository.
 * Prefers human-readable branch names over raw commit SHA hashes.
 */
export function getRepositoryDisplayBranch(repository: {
  current_ref?: string | null;
  default_branch?: string | null;
  last_indexed_commit?: string | null;
} | null | undefined): string {
  if (!repository) return "Unknown";

  const isSha = (str: string | null | undefined): boolean => {
    if (!str) return false;
    // Standard 40-character Git SHA-1 hash or exact match to last_indexed_commit
    return (
      /^[0-9a-f]{40}$/i.test(str) ||
      Boolean(repository.last_indexed_commit && str === repository.last_indexed_commit)
    );
  };

  // 1. If current_ref is a valid non-SHA branch name, use it (user-selected branch)
  if (repository.current_ref && !isSha(repository.current_ref)) {
    return repository.current_ref;
  }

  // 2. If default_branch is a valid non-SHA branch name, fallback to it
  if (repository.default_branch && !isSha(repository.default_branch)) {
    return repository.default_branch;
  }

  // 3. If only a SHA is available, return truncated short SHA or raw ref
  if (repository.current_ref) {
    return isSha(repository.current_ref)
      ? repository.current_ref.slice(0, 7)
      : repository.current_ref;
  }

  if (repository.default_branch) {
    return isSha(repository.default_branch)
      ? repository.default_branch.slice(0, 7)
      : repository.default_branch;
  }

  return "Unknown";
}


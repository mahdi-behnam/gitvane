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

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Not indexed";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

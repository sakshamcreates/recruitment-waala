const fullDate = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const shortDate = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

export function formatDate(value: string, compact = false) {
  return (compact ? shortDate : fullDate).format(
    new Date(value + "T00:00:00Z"),
  );
}

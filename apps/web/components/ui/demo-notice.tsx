import { Info } from "lucide-react";

export function DemoNotice({
  children = "Illustrative listings and dates. Applications and official notices are unavailable in this preview.",
}: {
  children?: string;
}) {
  return (
    <p className="demo-notice">
      <Info size={16} aria-hidden="true" />
      {children}
    </p>
  );
}

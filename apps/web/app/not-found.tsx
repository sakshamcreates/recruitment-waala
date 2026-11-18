import Link from "next/link";
import { buttonStyle } from "@/components/ui/primitives";

export default function NotFound() {
  return (
    <div className="state-box">
      <h1>Page unavailable</h1>
      <p>This route or illustrative listing could not be found.</p>
      <Link className={buttonStyle.primary} href="/search">
        Search opportunities
      </Link>
    </div>
  );
}

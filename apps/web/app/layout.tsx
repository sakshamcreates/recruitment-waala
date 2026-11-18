import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { Footer, Navbar } from "@/components/layout/site";
import { isDemo } from "@/lib/catalogue/repository";
import { getSiteOrigin } from "@/lib/metadata";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: getSiteOrigin(),
  title: {
    default: "Recruitment Waala — Every Opportunity. One Platform.",
    template: "%s | Recruitment Waala",
  },
  description:
    "Explore a catalogue of Indian government jobs, corporate roles, internships and exam updates.",
  robots: { index: !isDemo, follow: true },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en-IN" className={GeistSans.variable}>
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <Navbar />
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}

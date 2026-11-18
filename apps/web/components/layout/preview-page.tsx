import type { ReactNode } from "react";
import { Breadcrumbs } from "./breadcrumbs";
import { DemoNotice } from "@/components/ui/demo-notice";
import { PageContainer } from "@/components/ui/primitives";

export function PreviewPage({
  title,
  description,
  notice,
  children,
}: {
  title: string;
  description: string;
  notice: string;
  children: ReactNode;
}) {
  return (
    <PageContainer className="internal-page preview-page">
      <Breadcrumbs items={[{ label: title }]} />
      <header className="page-heading">
        <p className="eyebrow">Demonstration only</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>
      <DemoNotice>{notice}</DemoNotice>
      {children}
    </PageContainer>
  );
}

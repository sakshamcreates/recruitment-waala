import type { Metadata } from "next";
import { PreviewPage } from "@/components/layout/preview-page";
import { Card } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Moderation preview",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return (
    <PreviewPage
      title="Moderation desk"
      description="A preview of the work involved in checking sources, reviewing notices and publishing corrections."
      notice="Read-only demonstration. Source monitoring, reviewer access and publishing are unavailable."
    >
      <div className="admin-grid">
        <Card className="preview-card">
          <h2>Pending reviews</h2>
          <dl className="preview-list">
            <div>
              <dt>Assistant Audit Officer</dt>
              <dd>Sample review · Confirm recruitment cycle</dd>
            </div>
            <div>
              <dt>Civil Engineering Recruitment Test</dt>
              <dd>Sample review · Compare exam dates</dd>
            </div>
            <div>
              <dt>Clerical Services Examination</dt>
              <dd>Sample review · Check answer key stage</dd>
            </div>
          </dl>
        </Card>
        <Card className="preview-card">
          <h2>Source monitoring</h2>
          <dl className="preview-list">
            <div>
              <dt>Source registry</dt>
              <dd>No active sources in this preview</dd>
            </div>
            <div>
              <dt>Ingestion runs</dt>
              <dd>Monitoring unavailable</dd>
            </div>
          </dl>
        </Card>
        <Card className="preview-card">
          <h2>Recent changes</h2>
          <dl className="preview-list">
            <div>
              <dt>Deadline correction</dt>
              <dd>Example · Application closing date amended</dd>
            </div>
            <div>
              <dt>Notice categorisation</dt>
              <dd>Example · Exam stage clarified</dd>
            </div>
          </dl>
        </Card>
        <Card className="preview-card">
          <h2>Publishing status</h2>
          <dl className="preview-list">
            <div>
              <dt>Illustrative catalogue</dt>
              <dd>Preview records only</dd>
            </div>
            <div>
              <dt>Official publications</dt>
              <dd>Publishing unavailable</dd>
            </div>
          </dl>
        </Card>
      </div>
    </PreviewPage>
  );
}

import { FileText } from "lucide-react";
import Link from "next/link";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { DOC_TYPE, fmtDate, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { DocumentSummary } from "@/lib/types";
import { UploadForm } from "./UploadForm";

export default async function DocumentsPage() {
  const [me, docs] = await Promise.all([getMe(), api<DocumentSummary[]>("/api/documents")]);
  const name = me.ok ? fullName(me.data.subject) : "";
  return (
    <>
      <PageTitle eyebrow="Dokumente" title={`Dokumente von ${name}`}>
        Wir lesen nur, was ausdrücklich im Dokument steht – jede Empfehlung mit Zitat und Seitenzahl.
      </PageTitle>
      <div className="grid gap-6 lg:grid-cols-2">
        <UploadForm subjectName={name} />
        <section aria-labelledby="docs-h">
          <h2 id="docs-h" className="mb-3 text-lg font-semibold">
            Bisher hochgeladen
          </h2>
          {!docs.ok ? (
            <ApiError status={docs.status} detail={docs.detail} subjectName={name} />
          ) : docs.data.length === 0 ? (
            <p className="card text-muted">Noch keine Dokumente.</p>
          ) : (
            <ul className="space-y-3">
              {docs.data.map((d) => (
                <li key={d.document_id}>
                  <Link href={`/dokumente/${d.document_id}`} className="card flex items-center gap-4 hover:border-accent">
                    <FileText className="h-6 w-6 shrink-0 text-accent" aria-hidden />
                    <span className="flex-1">
                      <span className="block font-semibold">{d.filename}</span>
                      <span className="text-sm text-muted">
                        {DOC_TYPE[d.doc_type]} · hochgeladen {fmtDate(d.uploaded_at)}
                      </span>
                    </span>
                    <span className="link">Ansehen</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}

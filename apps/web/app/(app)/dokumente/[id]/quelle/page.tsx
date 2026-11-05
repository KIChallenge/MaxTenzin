import Link from "next/link";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { DOC_TYPE, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { DocumentSummary } from "@/lib/types";

/** Source view: the quoted passage plus the original document opened at the cited page. */
export default async function DocumentSourcePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ seite?: string; zitat?: string }>;
}) {
  const [{ id }, sp, me] = await Promise.all([params, searchParams, getMe()]);
  const docs = await api<DocumentSummary[]>("/api/documents");
  if (!docs.ok) return <ApiError status={docs.status} detail={docs.detail} subjectName={me.ok ? fullName(me.data.subject) : undefined} />;
  const doc = docs.data.find((d) => d.document_id === id);
  if (!doc) return <ApiError status={404} detail="Dieses Dokument gibt es für die gewählte Person nicht." />;
  const page = Number(sp.seite) || 1;
  const file = `/bff/api/documents/${encodeURIComponent(id)}/file?view=1#page=${page}`;

  return (
    <>
      <p className="mb-2 text-sm">
        <Link href={`/dokumente/${id}`} className="link">
          Zur Auswertung des Dokuments
        </Link>
      </p>
      <PageTitle title={`${doc.filename}, Seite ${page}`}>{DOC_TYPE[doc.doc_type]} – Originaldokument</PageTitle>
      {sp.zitat && (
        <figure className="mb-4 rounded-lg border-l-4 border-accent bg-accent-soft/60 px-4 py-3">
          <figcaption className="text-sm font-semibold text-muted">Zitierte Stelle auf Seite {page}</figcaption>
          <blockquote className="mt-1">„{sp.zitat}“</blockquote>
        </figure>
      )}
      <iframe
        title={`${doc.filename}, Seite ${page}`}
        src={file}
        className="h-[75vh] w-full rounded-xl border border-line bg-surface"
      />
      <p className="mt-2 text-sm text-muted">
        Wird das Dokument nicht angezeigt?{" "}
        <a className="link" href={file} target="_blank" rel="noreferrer">
          In neuem Tab öffnen
        </a>
      </p>
    </>
  );
}

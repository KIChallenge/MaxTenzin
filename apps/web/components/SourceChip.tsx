import { BookOpen, Coins, FileText, Link2, Paperclip, Pill, Scale, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { SourceRef } from "@/lib/types";
import { fmtDate } from "@/lib/labels";
import { ChipTooltip } from "./ChipTooltip";

const KIND_ICON: Record<string, LucideIcon> = {
  law: Scale,
  value: Coins,
  brochure: BookOpen,
  form: FileText,
  document: Paperclip,
  eko: Pill,
  external: Link2,
};
const KIND_LABEL: Record<string, string> = {
  law: "Gesetz",
  value: "Werte-Tabelle",
  brochure: "Broschüre",
  form: "Formular",
  document: "Ihr Dokument",
  eko: "Erstattungskodex",
  external: "Stammdaten",
};

/** Where a source can be read in full: law paragraph (with Absatz) or the cited page of the person's document.
 *  `documents` maps file names to document ids for sources that only carry "page:6" (e.g. eligibility criteria). */
export function sourceHref(s: SourceRef, documents?: Record<string, string>): string | null {
  const ref = s.ref ?? "";
  if (s.kind === "law") {
    const [key, kind, nr] = ref.split("=");
    if (key && kind === "PARA" && nr) {
      const abs = /Abs\.?\s*(\d+[a-z]?)/.exec(s.label)?.[1];
      return `/recht?law=${encodeURIComponent(key)}&nr=${encodeURIComponent(nr)}${abs ? `&abs=${abs}#abs-${abs}` : "#paragraf"}`;
    }
  }
  if (s.kind === "document") {
    const fromRef = /(?:document:)?(doc-[\w-]+)/.exec(ref)?.[1];
    const filename = s.label.split(/,\s*S\.|\s+–\s+/)[0]?.trim();
    const id = fromRef ?? (filename ? documents?.[filename] : undefined);
    const page = /page[:=](\d+)/.exec(ref)?.[1] ?? /S\.\s*(\d+)/.exec(s.label)?.[1];
    if (id) {
      const q = s.quote ? `&zitat=${encodeURIComponent(s.quote.slice(0, 500))}` : "";
      return `/dokumente/${id}/quelle?seite=${page ?? 1}${q}`;
    }
  }
  if (s.kind === "form") {
    const [formId, frag] = ref.split("#");
    const page = /page=(\d+)/.exec(frag ?? "")?.[1];
    if (formId && /^[a-z0-9_]+$/.test(formId)) return `/bff/api/forms/definitions/${formId}/template${page ? `#page=${page}` : ""}`;
  }
  if (s.kind === "brochure" && /Serviceratgeber/i.test(s.label)) {
    // Printed page "S. 63"; the PDF has two A5 pages per sheet.
    const printed = Number(/S\.\s*(\d+)/.exec(s.label)?.[1] ?? /page[:=](\d+)/.exec(ref)?.[1]);
    return `/bff/api/forms/brochures/serviceratgeber${printed ? `#page=${Math.floor(printed / 2) + 1}` : ""}`;
  }
  if (s.kind === "external" && /^https?:\/\//.test(ref)) return ref;
  return null;
}

/** Small source badge. Quote + Fassung shown on hover and keyboard focus; links to the full source when known. */
export function SourceChip({ source, documents }: { source: SourceRef; documents?: Record<string, string> }) {
  const href = sourceHref(source, documents);
  const Icon = KIND_ICON[source.kind];
  const detail = [
    KIND_LABEL[source.kind] ?? source.kind,
    source.in_force ? `Fassung in Kraft seit ${fmtDate(source.in_force)}` : null,
    source.quote ? `„${source.quote}"` : null,
  ].filter(Boolean);
  const cls = "inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-strong";
  const content = (
    <>
      {Icon && !(source.kind === "law" && source.label.trim().startsWith("§")) && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
      <span className="max-w-[16rem] truncate">{source.label}</span>
    </>
  );
  const label = `${href ? "Quelle öffnen" : "Quelle"}: ${source.label}. ${detail.join(". ")}`;
  const tip = (
    <>
      <strong className="block">{source.label}</strong>
      {detail.map((d) => (
        <span key={d} className="mt-1 block">
          {d}
        </span>
      ))}
    </>
  );
  return (
    <ChipTooltip tip={tip}>
      {!href ? (
        <span tabIndex={0} className={cls} aria-label={label}>
          {content}
        </span>
      ) : href.startsWith("/") && !href.startsWith("/bff/") ? (
        <Link href={href} className={`${cls} hover:border-accent hover:underline`} aria-label={label}>
          {content}
        </Link>
      ) : (
        <a href={href} target="_blank" rel="noreferrer" className={`${cls} hover:border-accent hover:underline`} aria-label={label}>
          {content}
        </a>
      )}
    </ChipTooltip>
  );
}

export function SourceList({ sources, documents }: { sources?: SourceRef[] | null; documents?: Record<string, string> }) {
  if (!sources?.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1.5">
      {sources.map((s, i) => (
        <SourceChip key={`${s.label}-${i}`} source={s} documents={documents} />
      ))}
    </span>
  );
}

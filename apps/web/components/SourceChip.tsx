import type { SourceRef } from "@/lib/types";
import { fmtDate } from "@/lib/labels";

const KIND_ICON: Record<string, string> = {
  law: "§",
  value: "€",
  brochure: "📘",
  form: "📄",
  document: "📎",
  eko: "💊",
  external: "🔗",
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

/** Small source badge. Quote + Fassung shown on hover and keyboard focus. */
export function SourceChip({ source }: { source: SourceRef }) {
  const detail = [
    KIND_LABEL[source.kind] ?? source.kind,
    source.in_force ? `Fassung in Kraft seit ${fmtDate(source.in_force)}` : null,
    source.quote ? `„${source.quote}"` : null,
  ].filter(Boolean);
  return (
    <span className="group relative inline-flex align-middle">
      <span
        tabIndex={0}
        className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 text-xs font-bold text-accent-strong"
        aria-label={`Quelle: ${source.label}. ${detail.join(". ")}`}
      >
        <span aria-hidden>{KIND_ICON[source.kind] ?? "•"}</span>
        {source.label}
      </span>
      <span
        role="tooltip"
        className="pointer-events-none invisible absolute bottom-full left-0 z-30 mb-2 w-72 rounded-lg bg-ink p-3 text-sm font-normal text-white opacity-0 shadow-lg transition-opacity group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
      >
        <strong className="block">{source.label}</strong>
        {detail.map((d) => (
          <span key={d} className="mt-1 block">
            {d}
          </span>
        ))}
      </span>
    </span>
  );
}

export function SourceList({ sources }: { sources?: SourceRef[] | null }) {
  if (!sources?.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1.5">
      {sources.map((s, i) => (
        <SourceChip key={`${s.label}-${i}`} source={s} />
      ))}
    </span>
  );
}

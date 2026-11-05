import { BookOpen, Coins, FileText, Link2, Paperclip, Pill, Scale, type LucideIcon } from "lucide-react";
import type { SourceRef } from "@/lib/types";
import { fmtDate } from "@/lib/labels";

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

/** Small source badge. Quote + Fassung shown on hover and keyboard focus. */
export function SourceChip({ source }: { source: SourceRef }) {
  const Icon = KIND_ICON[source.kind];
  const detail = [
    KIND_LABEL[source.kind] ?? source.kind,
    source.in_force ? `Fassung in Kraft seit ${fmtDate(source.in_force)}` : null,
    source.quote ? `„${source.quote}"` : null,
  ].filter(Boolean);
  return (
    <span className="group/chip relative inline-flex align-middle">
      <span
        tabIndex={0}
        className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-strong"
        aria-label={`Quelle: ${source.label}. ${detail.join(". ")}`}
      >
        {Icon && !(source.kind === "law" && source.label.trim().startsWith("§")) && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
        {source.label}
      </span>
      <span
        role="tooltip"
        className="pointer-events-none invisible absolute bottom-full left-0 z-30 mb-2 w-72 rounded-lg bg-ink p-3 text-sm font-normal text-white opacity-0 shadow-lg transition-opacity group-focus-within/chip:visible group-focus-within/chip:opacity-100 group-hover/chip:visible group-hover/chip:opacity-100"
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

import Link from "next/link";
import { ArrowRight, CalendarPlus, ClipboardList, FilePen, HelpCircle, Sparkles } from "lucide-react";
import type { components } from "@/lib/api-types";
import { ELIGIBILITY } from "@/lib/labels";
import { Badge } from "./Badge";
import { SourceChip } from "./SourceChip";

type Bundle = components["schemas"]["Bundle"];
type Item = components["schemas"]["BundleItem"];

/** Where an item of the bundle is handled in the cockpit. */
function itemHref(i: Item) {
  switch (i.kind) {
    case "benefit":
      return `/leistungen#${encodeURIComponent(i.ref_id)}`;
    case "form":
      return "/leistungen#antraege";
    case "appointment":
      return `/termine?topic=${encodeURIComponent(i.ref_id)}&suche=1`;
    case "case_step":
    case "step":
      return "/fall";
    case "prevention":
      return "/vorsorge";
    default:
      return null;
  }
}
const KIND_ICON = { form: FilePen, appointment: CalendarPlus, case_step: ClipboardList, step: ClipboardList } as const;

/** "Ihre Situation": benefits, forms, appointments and steps that belong together for one life situation. */
export function BundleCard({ bundle }: { bundle: Bundle | null }) {
  if (!bundle || !bundle.items?.length) return null;
  return (
    <section aria-labelledby="bundle-h" className="card space-y-3">
      <div>
        <h2 id="bundle-h" className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-4 w-4 text-accent" aria-hidden /> Ihre Situation: {bundle.title_de}
        </h2>
        {bundle.situation_de && <p className="text-muted">{bundle.situation_de}</p>}
      </div>
      <ul className="divide-y divide-line rounded-lg border border-line">
        {bundle.items.map((i) => {
          const href = itemHref(i);
          const Icon = KIND_ICON[i.kind as keyof typeof KIND_ICON];
          const st = i.status ? ELIGIBILITY[i.status] : null;
          const title = (
            <span className="inline-flex items-center gap-1.5 font-semibold">
              {Icon && <Icon className="h-4 w-4 text-accent" aria-hidden />}
              {i.title_de}
            </span>
          );
          return (
            <li key={i.kind + i.ref_id} className="flex flex-wrap items-start gap-x-3 gap-y-1 px-3 py-2">
              <span className="min-w-0 flex-1">
                {href ? (
                  <Link href={href} className="hover:underline">
                    {title}
                  </Link>
                ) : (
                  title
                )}
                {i.why_de && <span className="block text-sm text-muted">{i.why_de}</span>}
              </span>
              {st && <Badge tone={st.tone}>{st.label}</Badge>}
              {i.source && <SourceChip source={i.source} />}
            </li>
          );
        })}
      </ul>
      {bundle.questions_de?.length ? (
        <div>
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-muted">
            <HelpCircle className="h-4 w-4" aria-hidden /> Noch zu klären
          </h3>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {bundle.questions_de.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {bundle.next_step_de && (
        <p className="flex items-center gap-2 rounded-lg bg-accent-soft px-3 py-2 font-semibold text-accent-strong">
          <ArrowRight className="h-4 w-4" aria-hidden /> Nächster Schritt: {bundle.next_step_de}
        </p>
      )}
    </section>
  );
}

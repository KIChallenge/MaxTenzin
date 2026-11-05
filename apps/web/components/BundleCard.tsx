import Link from "next/link";
import { ArrowRight, Building2, CalendarPlus, FilePen, HelpCircle, Sparkles } from "lucide-react";
import { startForm } from "@/app/actions";
import type { components } from "@/lib/api-types";
import { ELIGIBILITY } from "@/lib/labels";
import { Badge } from "./Badge";
import { SourceChip } from "./SourceChip";

type Bundle = components["schemas"]["Bundle"];
type Item = components["schemas"]["BundleItem"];
const SHOWN = 4;

/**
 * "Ihre Situation": what belongs together for one life situation.
 * Forms are not separate rows – they become the "Antrag vorbereiten" action of the benefit they belong to.
 */
export function BundleCard({
  bundle,
  formOwner,
  documentId,
  canPrepare,
}: {
  bundle: Bundle | null;
  /** form_id → benefit_id (from the benefit catalog) */
  formOwner: Record<string, string>;
  documentId?: string;
  canPrepare: boolean;
}) {
  if (!bundle || !bundle.items?.length) return null;
  const formsOf = new Map<string, Item[]>();
  const looseForms: Item[] = [];
  for (const i of bundle.items.filter((x) => x.kind === "form")) {
    const owner = formOwner[i.ref_id];
    if (owner && bundle.items.some((b) => b.kind === "benefit" && b.ref_id === owner)) formsOf.set(owner, [...(formsOf.get(owner) ?? []), i]);
    else looseForms.push(i);
  }
  const first = bundle.items.filter((i) => i.kind === "appointment" || i.kind === "case_step" || i.kind === "step");
  const benefits = bundle.items.filter((i) => i.kind === "benefit");
  const offices = bundle.items.filter((i) => i.kind === "office");

  return (
    <section aria-labelledby="bundle-h" className="card space-y-3">
      <div>
        <h2 id="bundle-h" className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-4 w-4 text-accent" aria-hidden /> {bundle.title_de}
        </h2>
        {bundle.situation_de && <p className="text-sm text-muted">{bundle.situation_de}</p>}
      </div>

      {first.length > 0 && (
        <Group title="Als Erstes">
          {first.map((i) => (
            <Row key={i.kind + i.ref_id} item={i} icon={CalendarPlus} href={i.kind === "appointment" ? `/termine?topic=${encodeURIComponent(i.ref_id)}&suche=1` : "/fall"} />
          ))}
        </Group>
      )}

      {benefits.length > 0 && (
        <Group title="Leistungen">
          {benefits.slice(0, SHOWN).map((i) => (
            <Row key={i.ref_id} item={i} href={`/leistungen#${encodeURIComponent(i.ref_id)}`}>
              {(formsOf.get(i.ref_id) ?? []).map((f) => (
                <form key={f.ref_id} action={startForm}>
                  <input type="hidden" name="form_id" value={f.ref_id} />
                  <input type="hidden" name="benefit_id" value={i.ref_id} />
                  {documentId && <input type="hidden" name="document_id" value={documentId} />}
                  <button className="btn-secondary px-2.5 py-0.5 text-sm" disabled={!canPrepare} title={f.title_de}>
                    <FilePen className="h-3.5 w-3.5" aria-hidden /> Antrag vorbereiten
                  </button>
                </form>
              ))}
            </Row>
          ))}
          {looseForms.map((f) => (
            <Row key={f.ref_id} item={f} icon={FilePen} href="/leistungen#antraege" />
          ))}
          {benefits.length > SHOWN && (
            <li>
              <details className="group/more">
                <summary className="cursor-pointer list-none px-3 py-2 text-sm font-semibold text-accent hover:underline [&::-webkit-details-marker]:hidden">
                  <span className="group-open/more:hidden">Weitere {benefits.length - SHOWN} Leistungen anzeigen</span>
                  <span className="hidden group-open/more:inline">Weniger anzeigen</span>
                </summary>
                <ul className="divide-y divide-line border-t border-line">
                  {benefits.slice(SHOWN).map((i) => (
                    <Row key={i.ref_id} item={i} href={`/leistungen#${encodeURIComponent(i.ref_id)}`}>
                      {(formsOf.get(i.ref_id) ?? []).map((f) => (
                        <form key={f.ref_id} action={startForm}>
                          <input type="hidden" name="form_id" value={f.ref_id} />
                          <input type="hidden" name="benefit_id" value={i.ref_id} />
                          {documentId && <input type="hidden" name="document_id" value={documentId} />}
                          <button className="btn-secondary px-2.5 py-0.5 text-sm" disabled={!canPrepare} title={f.title_de}>
                            <FilePen className="h-3.5 w-3.5" aria-hidden /> Antrag vorbereiten
                          </button>
                        </form>
                      ))}
                    </Row>
                  ))}
                </ul>
              </details>
            </li>
          )}
        </Group>
      )}

      {offices.length > 0 && (
        <Group title="Zuständig">
          {offices.map((i) => (
            <Row key={i.ref_id} item={i} icon={Building2} href="/stellen" />
          ))}
        </Group>
      )}

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
        <p className="flex items-start gap-2 rounded-lg bg-accent-soft px-3 py-2 text-sm font-semibold text-accent-strong">
          <ArrowRight className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {bundle.next_step_de}
        </p>
      )}
    </section>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold text-muted">{title}</h3>
      <ul className="divide-y divide-line rounded-lg border border-line">{children}</ul>
    </div>
  );
}

function Row({
  item: i,
  href,
  icon: Icon,
  children,
}: {
  item: Item;
  href: string;
  icon?: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  children?: React.ReactNode;
}) {
  const st = i.status ? ELIGIBILITY[i.status] : null;
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
      <span className="min-w-0 flex-1">
        <Link href={href} className="inline-flex items-center gap-1.5 font-semibold hover:underline">
          {Icon && <Icon className="h-4 w-4 text-accent" aria-hidden />}
          {i.kind === "office" ? i.title_de.replace(/^Zuständig:\s*/, "") : i.title_de}
        </Link>
        {i.why_de && <span className="block text-sm text-muted">{i.why_de}</span>}
      </span>
      {st && <Badge tone={st.tone}>{st.label}</Badge>}
      {children}
      {i.source && <SourceChip source={i.source} />}
    </li>
  );
}

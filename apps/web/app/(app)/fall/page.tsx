import Link from "next/link";
import { ApiError } from "@/components/ApiError";
import { Badge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { fmtDate, fullName, STEP_STATUS } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Case } from "@/lib/types";
import { StepStatusSelect } from "./StepStatusSelect";

export default async function CasePage() {
  const [me, cases] = await Promise.all([getMe(), api<Case[]>("/api/cases")]);
  const name = me.ok ? fullName(me.data.subject) : "";
  return (
    <>
      <PageTitle eyebrow="Mein Fall" title={`Schritte für ${name}`}>
        Alles, was nach dem Spitalsaufenthalt zu tun ist – und wer dafür zuständig ist.
      </PageTitle>
      {!cases.ok ? (
        <ApiError status={cases.status} detail={cases.detail} subjectName={name} />
      ) : cases.data.length === 0 ? (
        <p className="card text-muted">
          Noch kein Fall angelegt. <Link href="/dokumente" className="link">Dokument hochladen</Link>, um Schritte zu erhalten.
        </p>
      ) : (
        cases.data.map((c) => {
          const done = c.steps.filter((s) => s.status === "done").length;
          return (
            <section key={c.id} className="mb-8">
              <div className="mb-3 flex flex-wrap items-end gap-3">
                <h2 className="text-2xl font-bold">{c.title_de}</h2>
                <span className="text-muted">
                  angelegt {fmtDate(c.created_at)} · {done} von {c.steps.length} erledigt
                </span>
              </div>
              <ol className="space-y-3">
                {c.steps.map((s, i) => {
                  const st = STEP_STATUS[s.status ?? "open"];
                  return (
                    <li key={s.id} className={`card flex flex-wrap items-center gap-4 ${s.status === "done" ? "opacity-75" : ""}`}>
                      <span aria-hidden className={`grid h-9 w-9 shrink-0 place-items-center rounded-full font-bold ${s.status === "done" ? "bg-ok text-white" : "bg-accent-soft text-accent-strong"}`}>
                        {s.status === "done" ? "✓" : i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className={`text-lg font-bold ${s.status === "done" ? "line-through" : ""}`}>{s.title_de}</p>
                        <p className="text-muted">
                          Zuständig: {s.responsible_de}
                          {s.due_date ? ` · bis ${fmtDate(s.due_date)}` : ""}
                        </p>
                        <div className="mt-1 flex flex-wrap gap-3">
                          {s.source && <SourceChip source={s.source} />}
                          {s.benefit_id && <Link href={`/leistungen#${s.benefit_id}`} className="link">Leistung ansehen</Link>}
                          {s.form_session_id && <Link href={`/forms/${s.form_session_id}`} className="link">Antrag öffnen</Link>}
                        </div>
                      </div>
                      <Badge tone={st.tone}>{st.label}</Badge>
                      <StepStatusSelect caseId={c.id} stepId={s.id} status={s.status ?? "open"} label={s.title_de} />
                    </li>
                  );
                })}
              </ol>
            </section>
          );
        })
      )}
    </>
  );
}

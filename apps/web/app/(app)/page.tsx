import { Building2, Compass, Eye, FilePen, FileText, ListChecks, Pill, Scale, Syringe } from "lucide-react";
import Link from "next/link";
import { CareTeamCard } from "@/components/CareTeamCard";
import { Lebenslage } from "@/components/Lebenslage";
import type { CareTeam } from "@/lib/care";
import { OpenChatButton } from "@/components/OpenChatButton";
import type { SituationOverview } from "@/lib/situation";
import { api } from "@/lib/api";
import { cockpitRoute, fmtDate, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Notification } from "@/lib/types";

const TILES = [
  { href: "/dokumente", icon: FileText, title: "Dokumente", text: "Entlassungsbrief hochladen – wir zeigen, was drinsteht." },
  { href: "/leistungen", icon: Compass, title: "Leistungen", text: "Welche Leistungen kommen in Frage – mit Quellen." },
  { href: "/leistungen#antraege", icon: FilePen, title: "Anträge", text: "Formulare vorausgefüllt vorbereiten, als PDF-Entwurf." },
  { href: "/fall", icon: ListChecks, title: "Mein Fall", text: "Alle Schritte nach dem Spitalsaufenthalt im Blick." },
  { href: "/vorsorge", icon: Syringe, title: "Vorsorge", text: "Impfungen und Vorsorgeuntersuchungen laut Impfplan." },
  { href: "/stellen", icon: Building2, title: "Zuständige Stellen", text: "Wo Sie welchen Antrag einreichen." },
  { href: "/medikamente", icon: Pill, title: "Medikamente", text: "Kosten und Bewilligung laut Erstattungskodex." },
  { href: "/recht", icon: Scale, title: "Rechtsgrundlagen", text: "Gesetzestexte mit gültiger Fassung." },
  { href: "/transparenz", icon: Eye, title: "Transparenz", text: "Wer hat wann was abgefragt – Mensch oder KI." },
];

export default async function Cockpit() {
  const [me, inbox, situation, team] = await Promise.all([
    getMe(),
    api<Notification[]>("/api/notifications"),
    api<SituationOverview>("/api/situation"),
    api<CareTeam>("/api/identity/care-team"),
  ]);
  const subject = me.ok ? me.data.subject : null;
  const actor = me.ok ? me.data.actor : null;
  const forOther = subject && actor && subject.id !== actor.id;
  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
      <section>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-[-0.02em]">
          Guten Tag, {actor?.first_name}
          {forOther && <span className="text-muted">. Sie handeln für {fullName(subject)}.</span>}
        </h1>
        <div className="mt-5">
          <Lebenslage
            {...(situation.ok ? { ok: true as const, data: situation.data } : { ok: false as const, status: situation.status, detail: situation.detail })}
            subjectName={subject ? fullName(subject) : ""}
            firstName={subject?.first_name ?? ""}
          />
        </div>
        <div className="card mt-5 flex flex-wrap items-center gap-4 border-accent/30 bg-accent-soft">
          <div className="flex-1">
            <p className="font-semibold">Was möchten Sie heute erledigen?</p>
            <p className="text-muted">Lotsi fragt die Dienste für Sie ab – mit denselben Berechtigungen wie Sie.</p>
          </div>
          <OpenChatButton>Frag Lotsi</OpenChatButton>
        </div>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {TILES.map((t) => (
            <li key={t.href}>
              <Link href={t.href} className="card flex h-full flex-col gap-1 transition hover:border-accent hover:shadow-md">
                <t.icon className="h-6 w-6 text-accent" aria-hidden />
                <span className="text-lg font-semibold text-accent-strong">{t.title}</span>
                <span className="text-muted">{t.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <aside aria-labelledby="inbox-h">
        <CareTeamCard team={team} firstName={subject?.first_name ?? ""} forOther={!!forOther} />
        <h2 id="inbox-h" className="text-lg font-semibold">
          Posteingang
        </h2>
        <div className="mt-3 space-y-3">
          {!inbox.ok && <p className="text-muted">Nachrichten derzeit nicht verfügbar.</p>}
          {inbox.ok && inbox.data.length === 0 && <p className="card text-muted">Keine neuen Nachrichten.</p>}
          {inbox.ok &&
            inbox.data.map((n) => (
              <article key={n.id} className={`card ${n.read ? "" : "border-l-4 border-l-accent"}`}>
                <p className="text-sm text-muted">{fmtDate(n.created_at)}</p>
                <h3 className="font-semibold">{n.title_de}</h3>
                <p className="text-muted">{n.body_de}</p>
                {n.link && (
                  <Link href={cockpitRoute(n.link)} className="link mt-1 inline-block">
                    Öffnen
                  </Link>
                )}
              </article>
            ))}
        </div>
      </aside>
    </div>
  );
}

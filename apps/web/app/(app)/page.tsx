import Link from "next/link";
import { OpenChatButton } from "@/components/OpenChatButton";
import { api } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Notification } from "@/lib/types";

const TILES = [
  { href: "/dokumente", icon: "📎", title: "Dokumente", text: "Entlassungsbrief hochladen – wir zeigen, was drinsteht." },
  { href: "/leistungen", icon: "🧭", title: "Leistungen", text: "Welche Leistungen kommen in Frage – mit Quellen." },
  { href: "/leistungen#antraege", icon: "📝", title: "Anträge", text: "Formulare vorausgefüllt vorbereiten, als PDF-Entwurf." },
  { href: "/fall", icon: "✅", title: "Mein Fall", text: "Alle Schritte nach dem Spitalsaufenthalt im Blick." },
  { href: "/vorsorge", icon: "💉", title: "Vorsorge", text: "Impfungen und Vorsorgeuntersuchungen laut Impfplan." },
  { href: "/stellen", icon: "🏢", title: "Zuständige Stellen", text: "Wo Sie welchen Antrag einreichen." },
  { href: "/medikamente", icon: "💊", title: "Medikamente", text: "Kosten und Bewilligung laut Erstattungskodex." },
  { href: "/recht", icon: "§", title: "Rechtsgrundlagen", text: "Gesetzestexte mit gültiger Fassung." },
  { href: "/transparenz", icon: "🔍", title: "Transparenz", text: "Wer hat wann was abgefragt – Mensch oder KI." },
];

export default async function Cockpit() {
  const [me, inbox] = await Promise.all([getMe(), api<Notification[]>("/api/notifications")]);
  const subject = me.ok ? me.data.subject : null;
  const actor = me.ok ? me.data.actor : null;
  const forOther = subject && actor && subject.id !== actor.id;
  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
      <section>
        <p className="eyebrow">Cockpit</p>
        <h1 className="text-3xl font-bold tracking-tight">
          Guten Tag, {actor?.first_name}
          {forOther && <span className="text-muted">. Sie handeln für {fullName(subject)}.</span>}
        </h1>
        <div className="card mt-5 flex flex-wrap items-center gap-4 border-accent/30 bg-accent-soft">
          <div className="flex-1">
            <p className="text-lg font-bold">Was möchten Sie heute erledigen?</p>
            <p className="text-muted">Der Lotse fragt die Dienste für Sie ab – mit denselben Berechtigungen wie Sie.</p>
          </div>
          <OpenChatButton>💬 Frag den Lotsen</OpenChatButton>
        </div>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {TILES.map((t) => (
            <li key={t.href}>
              <Link href={t.href} className="card flex h-full flex-col gap-1 transition hover:border-accent hover:shadow-md">
                <span aria-hidden className="text-3xl">
                  {t.icon}
                </span>
                <span className="text-xl font-bold text-accent-strong">{t.title}</span>
                <span className="text-muted">{t.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <aside aria-labelledby="inbox-h">
        <h2 id="inbox-h" className="text-xl font-bold">
          Posteingang
        </h2>
        <div className="mt-3 space-y-3">
          {!inbox.ok && <p className="text-muted">Nachrichten derzeit nicht verfügbar.</p>}
          {inbox.ok && inbox.data.length === 0 && <p className="card text-muted">Keine neuen Nachrichten.</p>}
          {inbox.ok &&
            inbox.data.map((n) => (
              <article key={n.id} className={`card ${n.read ? "" : "border-l-4 border-l-accent"}`}>
                <p className="text-sm text-muted">{fmtDate(n.created_at)}</p>
                <h3 className="font-bold">{n.title_de}</h3>
                <p className="text-muted">{n.body_de}</p>
                {n.link && (
                  <Link href={n.link} className="link mt-1 inline-block">
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

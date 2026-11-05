import Link from "next/link";
import { redirect } from "next/navigation";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { isPlain } from "@/lib/api";
import { fullName } from "@/lib/labels";
import { getMe, getRepresented } from "@/lib/me";

const NAV = [
  ["/", "Cockpit"],
  ["/dokumente", "Dokumente"],
  ["/leistungen", "Leistungen"],
  ["/fall", "Mein Fall"],
  ["/vorsorge", "Vorsorge"],
  ["/stellen", "Zuständige Stellen"],
  ["/medikamente", "Medikamente"],
  ["/recht", "Rechtsgrundlagen"],
  ["/transparenz", "Transparenz"],
] as const;

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const [me, rep, plain] = await Promise.all([getMe(), getRepresented(), isPlain()]);
  if (!me.ok) {
    if (me.status === 401 || me.status === 403) redirect("/login");
    return (
      <main className="mx-auto max-w-3xl p-8">
        <h1 className="text-2xl font-bold">Der Dienst ist gerade nicht erreichbar</h1>
        <p className="mt-2 text-muted">{me.detail} – läuft die API unter http://localhost:8000?</p>
      </main>
    );
  }
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-3">
        Zum Inhalt springen
      </a>
      <Header me={me.data} represented={rep.ok ? rep.data : [me.data.actor]} plain={plain} />
      <nav aria-label="Hauptnavigation" className="border-b border-line bg-surface">
        <ul className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-3">
          {NAV.map(([href, label]) => (
            <li key={href}>
              <Link href={href} className="block px-3 py-2.5 font-bold whitespace-nowrap text-muted hover:text-accent">
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <main id="main" className="mx-auto max-w-7xl px-5 py-8 pb-28">
        {children}
      </main>
      <footer className="mx-auto max-w-7xl px-5 pb-24 text-sm text-muted">
        Demo · Unverbindliche Information, keine Rechtsberatung und keine medizinische Beratung. Der Lotse sendet nie
        etwas ab – Sie prüfen, unterschreiben und senden selbst.
      </footer>
      <ChatPanel subjectId={me.data.subject.id} subjectName={fullName(me.data.subject)} plain={plain} />
    </>
  );
}

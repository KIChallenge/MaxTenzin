import { redirect } from "next/navigation";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { api, isPlain } from "@/lib/api";
import type { Preferences } from "@/lib/care";
import { fullName } from "@/lib/labels";
import { getMe, getRepresented } from "@/lib/me";


export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const [me, rep, plain, prefs, inbox] = await Promise.all([
    getMe(),
    getRepresented(),
    isPlain(),
    api<Preferences>("/api/identity/preferences"),
    api<{ read: boolean }[]>("/api/notifications"),
  ]);
  if (!me.ok) {
    if (me.status === 401 || me.status === 403) redirect("/login");
    return (
      <main className="mx-auto max-w-3xl p-8">
        <h1 className="text-xl font-semibold">Der Dienst ist gerade nicht erreichbar</h1>
        <p className="mt-2 text-muted">{me.detail} – läuft die API unter http://localhost:8000?</p>
      </main>
    );
  }
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-3">
        Zum Inhalt springen
      </a>
      <Header me={me.data} represented={rep.ok ? rep.data : [me.data.actor]} inboxCount={inbox.ok ? inbox.data.filter((n) => !n.read).length : 0} />
      <main id="main" className="mx-auto max-w-7xl px-5 py-6 pb-28">
        {children}
      </main>
      <footer className="mx-auto max-w-7xl px-5 pb-24 text-sm text-muted">
        Demo · Unverbindliche Information, keine Rechtsberatung und keine medizinische Beratung. Lotsi sendet nie
        etwas ab – Sie prüfen, unterschreiben und senden selbst.
      </footer>
      <ChatPanel subjectId={me.data.subject.id} subjectName={fullName(me.data.subject)} plain={plain} voice={prefs.ok && prefs.data.voice} />
    </>
  );
}

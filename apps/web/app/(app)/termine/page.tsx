import { Accessibility, CalendarDays } from "lucide-react";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { type Appointment, type CareTeam, type Preferences, type Slot, TOPICS, topicLabel } from "@/lib/care";
import { fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import { BookedList, SlotPicker } from "./TermineClient";

type SP = { provider?: string; topic?: string; daypart?: string; wo?: string; barrierefrei?: string; ab?: string; suche?: string };

export default async function AppointmentsPage({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const [me, prefs, team, booked] = await Promise.all([
    getMe(),
    api<Preferences>("/api/identity/preferences"),
    api<CareTeam>("/api/identity/care-team"),
    api<Appointment[]>("/api/appointments"),
  ]);
  const name = me.ok ? fullName(me.data.subject) : "";
  const firstName = me.ok ? me.data.subject.first_name : "";
  const gp = team.ok ? team.data.members.find((m) => m.role === "hausarzt") : undefined;

  // Defaults from the acting person's preferences; URL parameters win.
  const p = prefs.ok ? prefs.data : null;
  const where = sp.wo ?? (sp.provider ? "provider" : "near");
  const daypart = sp.daypart ?? (p?.daypart && p.daypart !== "any" ? p.daypart : "any");
  const accessible = sp.barrierefrei !== undefined ? sp.barrierefrei === "1" : !!p?.accessible;
  const providerId = where === "provider" ? (sp.provider ?? gp?.provider_id ?? undefined) : undefined;
  const topic = sp.topic ?? (providerId ? "hausarzt_kontrolle" : "");
  const doSearch = sp.suche === "1" || !!sp.provider;

  const slots = doSearch
    ? await api<Slot[]>("/api/appointments/slots/search", {
        method: "POST",
        body: {
          topic: providerId ? null : topic || null,
          provider_id: providerId ?? null,
          zip: me.ok ? me.data.subject.address.zip : null,
          near: where !== "provider",
          daypart,
          from_date: sp.ab || null,
          accessible_only: accessible,
          limit: 30,
        },
      })
    : null;

  return (
    <>
      <PageTitle title={`Termine für ${name}`}>Freie Termine suchen und buchen – Absagen jederzeit hier.</PageTitle>

      {booked.ok && booked.data.some((a) => a.status === "booked") && <BookedList appointments={booked.data.filter((a) => a.status === "booked")} />}
      {!booked.ok && booked.status === 403 && <ApiError status={403} detail={booked.detail} subjectName={name} />}

      <form className="card mb-5 grid gap-3 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_minmax(0,1fr)_9rem_auto] md:items-end" role="search">
        <input type="hidden" name="suche" value="1" />
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Anlass</span>
          <select name="topic" defaultValue={topic} className="input">
            <option value="">Bitte wählen …</option>
            {TOPICS.map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Wo</span>
          <select name="wo" defaultValue={where} className="input">
            {gp && <option value="provider">Bei {gp.name}</option>}
            <option value="near">In der Nähe von {firstName}</option>
            <option value="any">Egal wo</option>
          </select>
        </label>
        <fieldset className="flex flex-col gap-1">
          <legend className="mb-1 font-semibold">Tageszeit</legend>
          <div className="flex rounded-lg border border-line bg-surface p-0.5 text-sm">
            {[
              ["any", "egal"],
              ["morning", "vormittags"],
              ["afternoon", "nachmittags"],
            ].map(([v, l]) => (
              <label key={v} className="flex-1 cursor-pointer rounded-md px-2 py-1 text-center has-[:checked]:bg-accent has-[:checked]:font-semibold has-[:checked]:text-white">
                <input type="radio" name="daypart" value={v} defaultChecked={daypart === v} className="sr-only" />
                {l}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Ab</span>
          <input type="date" name="ab" defaultValue={sp.ab} className="input" />
        </label>
        <button className="btn-primary">Suchen</button>
        <label className="flex items-center gap-2 text-sm md:col-span-5">
          <input type="checkbox" name="barrierefrei" value="1" defaultChecked={accessible} className="h-4 w-4 accent-accent" />
          <Accessibility className="h-4 w-4 text-muted" aria-hidden /> Nur barrierefreie Ordinationen
          {p && <span className="ml-auto text-muted">Voreinstellungen aus Ihren Einstellungen</span>}
        </label>
      </form>

      {slots && !slots.ok && <ApiError status={slots.status} detail={slots.detail} subjectName={name} />}
      {slots?.ok && slots.data.length === 0 && (
        <p className="card text-muted">Keine freien Termine gefunden. Versuchen Sie eine andere Tageszeit oder „Egal wo“.</p>
      )}
      {slots?.ok && slots.data.length > 0 && <SlotPicker slots={slots.data} purpose={topicLabel(topic)} />}
      {!doSearch && (
        <p className="flex items-center gap-2 text-muted">
          <CalendarDays className="h-5 w-5" aria-hidden /> Wählen Sie einen Anlass und suchen Sie freie Termine.
        </p>
      )}
    </>
  );
}

"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Accessibility, CalendarCheck, CalendarPlus, Download, MapPin, X } from "lucide-react";
import { bff } from "@/lib/client";
import type { Appointment, Slot } from "@/lib/care";

const day = (iso: string) => new Date(iso).toLocaleDateString("de-AT", { weekday: "short", day: "numeric", month: "numeric" });
const time = (iso: string) => new Date(iso).toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
const DEFAULT_BRING = ["e-card", "Aktuelle Befunde (z. B. Entlassungsbrief)", "Medikamentenliste"];

/** Free slots grouped by day and practice; a click opens the booking box. */
export function SlotPicker({ slots, purpose }: { slots: Slot[]; purpose: string }) {
  const [chosen, setChosen] = useState<Slot | null>(null);
  const [done, setDone] = useState<Appointment | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const router = useRouter();

  const byDay = new Map<string, Map<string, Slot[]>>();
  for (const s of slots) {
    const d = s.start.slice(0, 10);
    const perProvider = byDay.get(d) ?? new Map<string, Slot[]>();
    perProvider.set(s.provider.id, [...(perProvider.get(s.provider.id) ?? []), s]);
    byDay.set(d, perProvider);
  }

  async function book(form: FormData) {
    if (!chosen) return;
    setMsg(null);
    const bring = form.getAll("bring").map(String);
    const r = await bff<Appointment>("/api/appointments", {
      method: "POST",
      body: { slot_id: chosen.id, purpose_de: String(form.get("purpose") || purpose), bring_documents_de: bring },
    });
    if (!r.ok) {
      setMsg(r.status === 409 ? "Dieser Termin wurde gerade vergeben – bitte wählen Sie einen anderen." : r.detail);
      if (r.status === 409) start(() => router.refresh());
      return;
    }
    setDone(r.data);
    setChosen(null);
    start(() => router.refresh());
  }

  return (
    <div className="space-y-4">
      {done && (
        <div role="status" className="card flex flex-wrap items-center gap-3 border-ok/30 bg-ok-soft">
          <CalendarCheck className="h-6 w-6 text-ok" aria-hidden />
          <p className="flex-1">
            <strong>Gebucht:</strong> {day(done.slot.start)}, {time(done.slot.start)} – {done.slot.provider.name}
            {done.notice_de && <span className="block text-sm text-muted">{done.notice_de}</span>}
          </p>
          <a href={`/bff${done.ics_url}`} className="btn-secondary py-1 text-sm">
            <Download className="h-4 w-4" aria-hidden /> In den Kalender
          </a>
        </div>
      )}
      {[...byDay.entries()].map(([d, providers]) => (
        <section key={d}>
          <h2 className="mb-1.5 font-semibold">{day(`${d}T12:00`)}</h2>
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
            {[...providers.values()].map((list) => {
              const p = list[0].provider;
              return (
                <li key={p.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
                  <div className="min-w-56 flex-1">
                    <p className="font-semibold">
                      {p.name}
                      {list[0].demo && <span className="ml-2 rounded-full bg-neutral-soft px-1.5 text-xs font-semibold text-muted">Demo-Termin</span>}
                    </p>
                    <p className="flex flex-wrap items-center gap-x-2 text-sm text-muted">
                      <MapPin className="h-3.5 w-3.5" aria-hidden /> {p.address}, {p.zip} {p.city} · {list[0].distance_hint_de}
                      {p.accessible && (
                        <span className="inline-flex items-center gap-1">
                          · <Accessibility className="h-3.5 w-3.5" aria-hidden /> barrierefrei
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {list.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => {
                          setChosen(s);
                          setMsg(null);
                        }}
                        aria-pressed={chosen?.id === s.id}
                        className="rounded-md border border-line px-2.5 py-1 text-sm font-semibold tabular-nums hover:border-accent hover:bg-accent-soft aria-pressed:border-accent aria-pressed:bg-accent aria-pressed:text-white"
                      >
                        {time(s.start)}
                      </button>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      {chosen && (
        <form
          action={book}
          className="card sticky bottom-4 z-20 space-y-3 border-accent/40 shadow-xl"
          aria-label="Termin buchen"
        >
          <div className="flex items-start gap-3">
            <CalendarPlus className="mt-0.5 h-5 w-5 text-accent" aria-hidden />
            <p className="flex-1">
              <strong>
                {day(chosen.start)}, {time(chosen.start)}–{time(chosen.end)}
              </strong>{" "}
              · {chosen.provider.name}
            </p>
            <button type="button" className="btn-ghost p-1" aria-label="Auswahl aufheben" onClick={() => setChosen(null)}>
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <label className="flex flex-col gap-1">
            <span className="font-semibold">Anlass</span>
            <input name="purpose" defaultValue={purpose} className="input" />
          </label>
          <fieldset>
            <legend className="font-semibold">Mitnehmen</legend>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {DEFAULT_BRING.map((b) => (
                <label key={b} className="inline-flex items-center gap-1.5">
                  <input type="checkbox" name="bring" value={b} defaultChecked className="h-4 w-4 accent-accent" /> {b}
                </label>
              ))}
            </div>
          </fieldset>
          {msg && (
            <p role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
              {msg}
            </p>
          )}
          <div className="flex items-center gap-3">
            <button className="btn-primary" disabled={pending}>
              Termin buchen
            </button>
            <span className="text-sm text-muted">Demo – es wird kein echter Termin vergeben.</span>
          </div>
        </form>
      )}
    </div>
  );
}

/** Booked appointments with calendar download and cancel. */
export function BookedList({ appointments }: { appointments: Appointment[] }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  const sorted = [...appointments].sort((a, b) => a.slot.start.localeCompare(b.slot.start));
  return (
    <section aria-labelledby="booked-h" className="mb-5">
      <h2 id="booked-h" className="mb-1.5 text-lg font-semibold">
        Gebuchte Termine
      </h2>
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
        {sorted.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5">
            <span className="w-36 font-semibold tabular-nums">
              {day(a.slot.start)}, {time(a.slot.start)}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate">{a.slot.provider.name}</span>
              <span className="block truncate text-sm text-muted">
                {a.purpose_de}
                {a.bring_documents_de?.length ? ` · mitnehmen: ${a.bring_documents_de.join(", ")}` : ""}
              </span>
            </span>
            <a href={`/bff${a.ics_url}`} className="btn-ghost py-1 text-sm">
              <Download className="h-4 w-4" aria-hidden /> Kalender
            </a>
            <button
              type="button"
              className="btn-ghost py-1 text-sm text-danger hover:bg-danger-soft"
              disabled={pending}
              onClick={() =>
                start(async () => {
                  await bff(`/api/appointments/${a.id}/cancel`, { method: "POST" });
                  router.refresh();
                })
              }
            >
              Absagen
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

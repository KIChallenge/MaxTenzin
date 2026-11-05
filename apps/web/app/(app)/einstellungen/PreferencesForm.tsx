"use client";
// Preferences of the acting person (GET/PUT /api/identity/preferences). Lotsi reads them every turn;
// the Termine search uses them as defaults.
import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import type { Preferences } from "@/lib/care";

function Segmented<T extends string>({ label, hint, value, options, onChange }: { label: string; hint?: string; value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
      <div className="min-w-48 flex-1">
        <p className="font-semibold">{label}</p>
        {hint && <p className="text-sm text-muted">{hint}</p>}
      </div>
      <div role="radiogroup" aria-label={label} className="flex rounded-lg border border-line bg-paper p-0.5 text-sm">
        {options.map(([v, l]) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={value === v}
            onClick={() => onChange(v)}
            className={`rounded-md px-3 py-1 ${value === v ? "bg-surface font-semibold shadow-sm" : "text-muted hover:text-ink"}`}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

function Switch({ label, hint, on, onChange }: { label: string; hint?: string; on: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center gap-4 px-4 py-3">
      <div className="flex-1">
        <p className="font-semibold">{label}</p>
        {hint && <p className="text-sm text-muted">{hint}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        onClick={() => onChange(!on)}
        className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${on ? "bg-accent" : "bg-muted/35"}`}
      >
        <span className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all ${on ? "left-[1.375rem]" : "left-0.5"}`} />
      </button>
    </div>
  );
}

export function PreferencesForm({ initial, actorFirstName }: { initial: Preferences; actorFirstName: string }) {
  const [p, setP] = useState(initial);
  const [err, setErr] = useState<string | null>(null);
  const [, start] = useTransition();
  const router = useRouter();

  // PUT replaces the whole object → always send the complete, latest state (ref survives quick consecutive clicks).
  const latest = useRef(initial);
  function set<K extends keyof Preferences>(key: K, value: Preferences[K]) {
    const prev = latest.current;
    const next = { ...latest.current, [key]: value };
    latest.current = next;
    setP(next);
    start(async () => {
      const r = await bff<Preferences>("/api/identity/preferences", { method: "PUT", body: next });
      if (!r.ok) {
        latest.current = prev;
        setP(prev);
        setErr(r.detail);
      } else {
        setErr(null);
        router.refresh();
      }
    });
  }

  // Known only in the browser – decided after mount to keep server and client markup identical.
  const [voiceSupported, setVoiceSupported] = useState(true);
  useEffect(() => setVoiceSupported("SpeechRecognition" in window || "webkitSpeechRecognition" in window), []);
  const box = "divide-y divide-line rounded-xl border border-line bg-surface";
  return (
    <>
      <section aria-labelledby="lotsi-h" className="mb-8">
        <h2 id="lotsi-h" className="mb-2 text-lg font-semibold">
          Lotsi <span className="text-sm font-normal text-muted">– Ihre Einstellungen ({actorFirstName})</span>
        </h2>
        <div className={box}>
          <Segmented
            label="Antworten von Lotsi"
            hint="Wie ausführlich Lotsi antwortet."
            value={p.detail}
            options={[
              ["short", "kurz"],
              ["normal", "normal"],
              ["detailed", "ausführlich"],
            ]}
            onChange={(v) => set("detail", v)}
          />
          <Switch
            label="Spracheingabe"
            hint={
              voiceSupported
                ? "Mikrofon im Chat: sprechen statt tippen (Deutsch, Österreich). Sie schicken die Nachricht selbst ab."
                : "Ihr Browser unterstützt keine Spracheingabe (z. B. Chrome oder Safari verwenden)."
            }
            on={p.voice}
            onChange={(v) => set("voice", v)}
          />
        </div>
      </section>
      <section aria-labelledby="termine-h" className="mb-8">
        <h2 id="termine-h" className="mb-2 text-lg font-semibold">
          Termine
        </h2>
        <div className={box}>
          <Segmented
            label="Bevorzugte Tageszeit"
            value={(p.daypart as "any" | "morning" | "afternoon") ?? "any"}
            options={[
              ["any", "egal"],
              ["morning", "vormittags"],
              ["afternoon", "nachmittags"],
            ]}
            onChange={(v) => set("daypart", v)}
          />
          <Switch label="In der Nähe" hint="Termine zuerst in der Nähe der Wohnadresse suchen." on={p.near_home} onChange={(v) => set("near_home", v)} />
          <Switch label="Nur barrierefrei" hint="Nur Ordinationen mit barrierefreiem Zugang anzeigen." on={p.accessible} onChange={(v) => set("accessible", v)} />
        </div>
        {err && <p className="mt-2 text-sm text-danger">{err}</p>}
      </section>
    </>
  );
}

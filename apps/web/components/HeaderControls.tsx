"use client";
import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { setLargeText, setPlain, setSubject } from "@/app/actions";

export function SubjectSwitcher({ current, options }: { current: string; options: { id: string; name: string }[] }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <label className="inline-flex items-center gap-1.5">
      <span className="text-muted">Für</span>
      <select
        className="max-w-48 rounded-md border border-line bg-surface py-1 pr-7 pl-2 font-semibold text-ink"
        value={current}
        disabled={pending}
        onChange={(e) =>
          start(async () => {
            await setSubject(e.target.value);
            router.refresh();
          })
        }
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}

/** A settings row with an iOS-style switch. */
function SettingSwitch({ on, label, hint, onToggle }: { on: boolean; label: string; hint: string; onToggle: (next: boolean) => Promise<void> }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <div className="flex items-center gap-4 px-4 py-3">
      <div className="flex-1">
        <p className="font-semibold">{label}</p>
        <p className="text-sm text-muted">{hint}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        disabled={pending}
        onClick={() =>
          start(async () => {
            await onToggle(!on);
            router.refresh();
          })
        }
        className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${on ? "bg-accent" : "bg-muted/35"}`}
      >
        <span className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all ${on ? "left-[1.375rem]" : "left-0.5"}`} />
      </button>
    </div>
  );
}

export function PlainToggle({ on }: { on: boolean }) {
  return <SettingSwitch on={on} label="Einfache Sprache" hint="Kürzere Sätze und einfache Erklärungen – auch in den Antworten von Lotsi." onToggle={setPlain} />;
}

export function LargeTextToggle({ on }: { on: boolean }) {
  return <SettingSwitch on={on} label="Größere Schrift" hint="Alle Texte etwas größer. Sie können auch im Browser zoomen (⌘ +)." onToggle={setLargeText} />;
}

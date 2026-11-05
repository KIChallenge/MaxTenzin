"use client";
import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { setPlain, setSubject } from "@/app/actions";

export function SubjectSwitcher({ current, options }: { current: string; options: { id: string; name: string }[] }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <label className="inline-flex items-center gap-2">
      <span className="text-muted">für</span>
      <select
        className="rounded-lg border border-accent bg-surface px-2 py-1 font-bold text-accent-strong"
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

export function PlainToggle({ on }: { on: boolean }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      disabled={pending}
      onClick={() =>
        start(async () => {
          await setPlain(!on);
          router.refresh();
        })
      }
      className="inline-flex items-center gap-2 rounded-lg px-2 py-1 font-bold text-accent hover:bg-accent-soft"
    >
      <span
        aria-hidden
        className={`relative inline-block h-5 w-9 rounded-full transition-colors ${on ? "bg-accent" : "bg-muted/40"}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${on ? "left-4.5" : "left-0.5"}`} />
      </span>
      Einfache Sprache
    </button>
  );
}

import type { Tone } from "@/lib/labels";

const TONES: Record<Tone, string> = {
  ok: "bg-ok-soft text-ok border-ok/30",
  warn: "bg-warn-soft text-warn border-warn/30",
  info: "bg-info-soft text-info border-info/30",
  neutral: "bg-neutral-soft text-neutral border-neutral/30",
  danger: "bg-danger-soft text-danger border-danger/30",
};

export function Badge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-sm font-semibold ${TONES[tone]}`}>
      {children}
    </span>
  );
}

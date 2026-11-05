import Link from "next/link";
import { SCOPE_LABELS } from "@/lib/labels";

/** API details name scopes by key ("Fehlende Berechtigung 'view_health_prevention'") – show the German name instead. */
function humanize(detail: string) {
  return detail.replace(/'?\b(read_documents|prepare_applications|manage_appointments|view_health_prevention|manage_case|manage_situation)\b'?/g, (_, k: keyof typeof SCOPE_LABELS) => `„${SCOPE_LABELS[k]}“`);
}

/** Friendly rendering of an API error. 403 explains the missing delegation. */
export function ApiError({ status, detail, subjectName }: { status: number; detail: string; subjectName?: string }) {
  if (status === 403) {
    return (
      <div role="alert" className="card border-warn/40 bg-warn-soft">
        <p className="font-semibold text-ink">
          Dafür hat {subjectName ?? "die vertretene Person"} keine Berechtigung erteilt.
        </p>
        <p className="mt-1 text-muted">{humanize(detail)}</p>
        <p className="mt-3">
          <Link href="/einstellungen#vollmachten" className="link">
            Vollmachten ansehen
          </Link>
        </p>
      </div>
    );
  }
  return (
    <div role="alert" className="card border-danger/40 bg-danger-soft">
      <p className="font-semibold text-danger">Das hat leider nicht geklappt{status ? ` (Fehler ${status})` : ""}.</p>
      <p className="mt-1 text-ink">{detail}</p>
    </div>
  );
}

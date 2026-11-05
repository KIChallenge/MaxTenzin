import Link from "next/link";

/** Friendly rendering of an API error. 403 explains the missing delegation. */
export function ApiError({ status, detail, subjectName }: { status: number; detail: string; subjectName?: string }) {
  if (status === 403) {
    return (
      <div role="alert" className="card border-warn/40 bg-warn-soft">
        <p className="text-lg font-bold text-ink">
          Dafür hat {subjectName ?? "die vertretene Person"} keine Berechtigung erteilt.
        </p>
        <p className="mt-1 text-muted">{detail}</p>
        <p className="mt-3">
          <Link href="/vertretung" className="link">
            Vertretung &amp; Berechtigungen ansehen
          </Link>
        </p>
      </div>
    );
  }
  return (
    <div role="alert" className="card border-danger/40 bg-danger-soft">
      <p className="font-bold text-danger">Das hat leider nicht geklappt{status ? ` (Fehler ${status})` : ""}.</p>
      <p className="mt-1 text-ink">{detail}</p>
    </div>
  );
}

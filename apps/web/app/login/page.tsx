import { login } from "@/app/actions";
import { api } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/labels";
import type { Person } from "@/lib/types";

// Order on stage: demo 1 (Maria acts for Anna), then demo 2 (Stefan, with his daughter Lena).
const GROUPS: { title: string; ids: string[] }[] = [
  { title: "Demo 1 – Pflege nach dem Spital", ids: ["maria", "anna"] },
  { title: "Demo 2 – Gesundheit & Familie", ids: ["stefan", "lena"] },
];

const ROLE: Record<string, string> = {
  maria: "Tochter, vertritt ihre Mutter Anna",
  anna: "Pensionistin, nach Spitalsaufenthalt",
  stefan: "Vater, Vorsorge für sich und Tochter Lena · Sprache Englisch",
  lena: "Kind (wird von Stefan vertreten)",
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  const personas = await api<Person[]>("/api/identity/personas");
  return (
    <main className="mx-auto max-w-3xl px-5 py-12">
      <p className="eyebrow">Demo-Anmeldung</p>
      <h1 className="text-4xl font-semibold tracking-tight">Anmelden mit ID Austria</h1>
      <p className="mt-2 text-lg text-muted">
        Simulierte Anmeldung. Wählen Sie eine Demo-Person. Lotsi, die KI, arbeitet danach ausschließlich mit den
        Berechtigungen dieser Person.
      </p>
      {error && (
        <p role="alert" className="card mt-6 border-danger/40 bg-danger-soft text-danger">
          {error}
        </p>
      )}
      {!personas.ok ? (
        <p role="alert" className="card mt-6 border-danger/40 bg-danger-soft">
          Der Anmeldedienst ist nicht erreichbar ({personas.detail}). Läuft die API unter http://localhost:8000?
        </p>
      ) : (
        <div className="mt-8 space-y-8">
          {[
            ...GROUPS,
            { title: "Weitere Personen", ids: personas.data.map((p) => p.id).filter((id) => !GROUPS.some((g) => g.ids.includes(id))) },
          ]
            .filter((g) => g.ids.length)
            .map((g) => (
              <section key={g.title} aria-label={g.title}>
                <h2 className="mb-3 text-sm font-semibold tracking-wide text-muted uppercase">{g.title}</h2>
                <ul className="grid gap-4 sm:grid-cols-2">
                  {g.ids
                    .map((id) => personas.data.find((p) => p.id === id))
                    .filter((p): p is Person => !!p)
                    .map((p) => (
                      <li key={p.id}>
                        <form action={login}>
                          <input type="hidden" name="persona_id" value={p.id} />
                          <button className="card flex w-full flex-col items-start text-left transition hover:border-accent hover:shadow-md">
                            <span className="text-lg font-semibold text-accent-strong">{fullName(p)}</span>
                            <span className="text-muted">{ROLE[p.id] ?? ""}</span>
                            <span className="mt-2 text-sm text-muted">
                              geb. {fmtDate(p.birth_date)} · {p.insurer}
                            </span>
                            <span className="btn-primary mt-4">Als {p.first_name} anmelden</span>
                          </button>
                        </form>
                      </li>
                    ))}
                </ul>
              </section>
            ))}
        </div>
      )}
    </main>
  );
}

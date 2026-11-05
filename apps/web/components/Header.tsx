import { LogOut, Sailboat, Settings } from "lucide-react";
import Link from "next/link";
import { logout } from "@/app/actions";
import { fullName, SCOPE_LABELS } from "@/lib/labels";
import type { Person, Session } from "@/lib/types";
import { SubjectSwitcher } from "./HeaderControls";
import { NavBar } from "./NavBar";

/** One translucent, sticky bar: brand · navigation · (person switch) · settings · sign-out.
 *  The person switch and the permission line only exist when the user may act for someone else. */
export function Header({ me, represented }: { me: Session; represented: Person[] }) {
  const actingForOther = me.actor.id !== me.subject.id;
  const canRepresent = represented.some((p) => p.id !== me.actor.id);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur-xl backdrop-saturate-150">
      <div className="@container mx-auto max-w-7xl px-5">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
          <Link href="/" className="flex items-center gap-2 text-[1.0625rem] font-semibold tracking-[-0.01em] text-ink">
            <span aria-hidden className="grid h-7 w-7 place-items-center rounded-md bg-accent text-white">
              <Sailboat className="h-4 w-4" />
            </span>
            KI-Lotse
          </Link>
          <div className="order-last w-full @5xl:order-none @5xl:w-auto">
            <NavBar />
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-[0.9375rem]">
            {canRepresent ? (
              <SubjectSwitcher
                current={me.subject.id}
                options={[...represented]
                  .sort((a, b) => (a.id === me.actor.id ? -1 : b.id === me.actor.id ? 1 : 0))
                  .map((p) => {
                    const relation = me.delegations?.find((d) => d.grantor_id === p.id && d.grantee_id === me.actor.id)?.relation;
                    return {
                      id: p.id,
                      name: fullName(p),
                      initials: `${p.first_name[0] ?? ""}${p.last_name[0] ?? ""}`,
                      sub: p.id === me.actor.id ? "Sie selbst" : relation ? `Vertretung: ${relation}` : "Vertretung",
                    };
                  })}
              />
            ) : (
              <span className="text-muted">{fullName(me.actor)}</span>
            )}
            <Link href="/einstellungen" className="rounded-md p-1.5 text-muted hover:bg-neutral-soft hover:text-ink" title="Einstellungen">
              <Settings className="h-5 w-5" aria-hidden />
              <span className="sr-only">Einstellungen</span>
            </Link>
            <form action={logout}>
              <button className="rounded-md p-1.5 text-muted hover:bg-neutral-soft hover:text-ink" title="Abmelden">
                <LogOut className="h-5 w-5" aria-hidden />
                <span className="sr-only">Abmelden</span>
              </button>
            </form>
          </div>
        </div>
      </div>
      {actingForOther && (
        <div className="border-t border-accent/15 bg-accent-soft/70">
          <p className="mx-auto max-w-7xl px-5 py-1 text-sm">
            <strong className="font-semibold">{fullName(me.actor)}</strong> handelt für{" "}
            <strong className="font-semibold">{fullName(me.subject)}</strong>
            <span className="text-muted"> · erlaubt: {me.scopes.map((s) => SCOPE_LABELS[s]).join(", ")} · </span>
            <Link href="/einstellungen#vollmachten" className="link">
              Vollmacht ansehen
            </Link>
          </p>
        </div>
      )}
    </header>
  );
}

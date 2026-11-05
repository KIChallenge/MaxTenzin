import Link from "next/link";
import { logout } from "@/app/actions";
import { fullName, SCOPE_LABELS } from "@/lib/labels";
import type { Person, Session } from "@/lib/types";
import { PlainToggle, SubjectSwitcher } from "./HeaderControls";

export function Header({ me, represented, plain }: { me: Session; represented: Person[]; plain: boolean }) {
  const actingForOther = me.actor.id !== me.subject.id;
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
        <Link href="/" className="flex items-center gap-2 text-xl font-bold text-accent-strong">
          <span aria-hidden className="grid h-9 w-9 place-items-center rounded-lg bg-accent text-white">
            ⛵
          </span>
          KI-Lotse
        </Link>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>
            <span className="sr-only">Angemeldet als </span>
            <strong>{fullName(me.actor)}</strong>
          </span>
          <span aria-hidden className="text-line">
            ·
          </span>
          <SubjectSwitcher
            current={me.subject.id}
            options={represented.map((p) => ({ id: p.id, name: p.id === me.actor.id ? `${fullName(p)} (ich)` : fullName(p) }))}
          />
        </div>
        <div className="ml-auto flex items-center gap-2">
          <PlainToggle on={plain} />
          <form action={logout}>
            <button className="btn-ghost">Abmelden</button>
          </form>
        </div>
      </div>
      <div className={`border-t border-line ${actingForOther ? "bg-accent-soft" : "bg-paper"}`}>
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-2 gap-y-1 px-5 py-1.5 text-sm">
          <span className="font-bold text-ink">
            {actingForOther ? `${me.subject.first_name} erlaubt Ihnen:` : "Ihre Berechtigungen:"}
          </span>
          {me.scopes.map((s) => (
            <span key={s} className="rounded-full border border-accent/30 bg-surface px-2 py-px font-bold text-accent-strong">
              ✓ {SCOPE_LABELS[s]}
            </span>
          ))}
          <Link href="/vertretung" className="link ml-auto">
            Vertretung
          </Link>
        </div>
      </div>
    </header>
  );
}

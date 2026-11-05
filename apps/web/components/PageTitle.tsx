/** Page heading: one clear title, optional one-line context. (The small label above titles was dropped – the active nav item already says where you are.) */
export function PageTitle({ title, children }: { eyebrow?: string; title: string; children?: React.ReactNode }) {
  return (
    <header className="mb-5">
      <h1 className="text-[1.75rem] leading-tight font-semibold tracking-[-0.02em] text-ink">{title}</h1>
      {children && <div className="mt-1.5 max-w-3xl text-muted">{children}</div>}
    </header>
  );
}

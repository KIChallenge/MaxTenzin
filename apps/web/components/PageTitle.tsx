export function PageTitle({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: React.ReactNode }) {
  return (
    <header className="mb-6">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1 className="text-3xl font-bold tracking-tight text-ink">{title}</h1>
      {children && <div className="mt-2 max-w-3xl text-lg text-muted">{children}</div>}
    </header>
  );
}

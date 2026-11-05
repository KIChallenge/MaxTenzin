/** Lotsi – the Lotse's persona: a friendly, gender-neutral ship's pilot (cap + compass), deliberately not a doctor. */
export function LotsiAvatar({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="Lotsi" className={className}>
      <circle cx="32" cy="32" r="31" fill="var(--color-accent-soft)" />
      {/* face */}
      <circle cx="32" cy="37" r="17" fill="#f6d7b8" />
      <circle cx="25.5" cy="37" r="2.2" fill="var(--color-ink)" />
      <circle cx="38.5" cy="37" r="2.2" fill="var(--color-ink)" />
      <path d="M26 44 Q32 49 38 44" stroke="var(--color-ink)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      <circle cx="21.5" cy="42" r="2.4" fill="#f2a98f" opacity="0.7" />
      <circle cx="42.5" cy="42" r="2.4" fill="#f2a98f" opacity="0.7" />
      {/* pilot cap */}
      <path d="M14 27 Q32 10 50 27 Z" fill="#001e50" />
      <rect x="12" y="25.5" width="40" height="5" rx="2.5" fill="#001e50" />
      <rect x="15" y="28.5" width="34" height="2.2" rx="1.1" fill="var(--color-accent)" />
      {/* compass badge */}
      <circle cx="32" cy="20.5" r="4.6" fill="#ffffff" />
      <path d="M32 16.8 L33.6 20.5 L32 24.2 L30.4 20.5 Z" fill="var(--color-accent)" />
    </svg>
  );
}

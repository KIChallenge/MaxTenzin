// Chat replies end with a free-text "Quelle(n): …" block written by the model. We split it off the reply and show
// each source as a small pill – clickable when the target is unambiguous (document page, law paragraph, brochure page).

export type DocRef = { document_id: string; filename: string };
export type LawRef = { key: string; abbr: string };

const HEADER = /^[ \t]*[*_]{0,2}\s*(quellen?|sources?)\s*[*_]{0,2}\s*:\s*[*_]{0,2}/gim;
const NOTE = /unverbindlich|keine rechtsberatung|not legal advice/i;

const clean = (s: string) =>
  s
    .replace(/^[\s\-•*·]+/, "")
    .replace(/[`*_]+/g, "")
    .replace(/\s+/g, " ")
    .replace(/[.;,]\s*$/, "")
    .trim();

/** "BPGG § 3, § 4, § 5" → ["§ 3 BPGG", "§ 4 BPGG", "§ 5 BPGG"]; anything else stays one item. */
function expandLaw(item: string): string[] {
  const paras = item.match(/§\s*\d+[a-z]?(?:\s*Abs\.\s*\d+[a-z]?)?/g);
  if (!paras || paras.length < 2) return [item];
  const law = clean(item.replace(/§\s*\d+[a-z]?(?:\s*Abs\.\s*\d+[a-z]?)?/g, "").replace(/\([^)]*\)/g, "").replace(/,/g, " "));
  return paras.map((p) => `${p.replace(/\s+/g, " ")} ${law}`.trim());
}

export function splitSources(text: string): { body: string; sources: string[]; note: string | null } {
  // the LAST "Quelle(n):" line (at a line start, with colon) starts the trailing source block
  const m = [...text.matchAll(HEADER)].pop();
  if (!m || m.index === undefined) return { body: text, sources: [], note: null };
  const body = text.slice(0, m.index).trimEnd();
  const block = text.slice(m.index + m[0].length);
  const items = block
    .split(/\n|;|\s[—–]\s/)
    .map(clean)
    .filter(Boolean);
  const notes = items.filter((i) => NOTE.test(i));
  const sources = [...new Set(items.filter((i) => !NOTE.test(i)).flatMap(expandLaw))];
  return { body, sources, note: notes.length ? notes.join(" ") : null };
}

const norm = (s: string) =>
  s
    .toLowerCase()
    .replace(/ö/g, "oe")
    .replace(/ä/g, "ae")
    .replace(/ü/g, "ue")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

function lawHref(label: string, laws: LawRef[]): string | null {
  const nr = /§\s*(\d+[a-z]?)/.exec(label)?.[1];
  if (!nr) return null;
  const abs = /Abs\.\s*(\d+[a-z]?)/.exec(label)?.[1];
  const tokens = new Set(norm(label.replace(/\([^)]*\)/g, "")).split(" "));
  const hit = laws
    .filter((l) => norm(l.abbr).split(" ").every((t) => tokens.has(t)))
    .sort((a, b) => b.abbr.length - a.abbr.length)[0];
  if (!hit) return null;
  return `/recht?law=${encodeURIComponent(hit.key)}&nr=${encodeURIComponent(nr)}${abs ? `&abs=${abs}#abs-${abs}` : "#paragraf"}`;
}

function docHref(label: string, docs: DocRef[]): string | null {
  const name = norm(label.split(/,\s*(?:S\.|p\.|pp\.|page)/i)[0]);
  const doc = docs.find((d) => {
    const f = norm(d.filename);
    return f && (name.startsWith(f) || f.startsWith(name));
  });
  if (!doc) return null;
  const page = /(?:S\.|p\.|pp\.|page)\s*(\d+)/i.exec(label)?.[1] ?? "1";
  return `/dokumente/${doc.document_id}/quelle?seite=${page}`;
}

function brochureHref(label: string): string | null {
  if (!/serviceratgeber/i.test(label)) return null;
  const printed = Number(/S\.\s*(\d+)/.exec(label)?.[1]);
  return `/bff/api/forms/brochures/serviceratgeber${printed ? `#page=${Math.floor(printed / 2) + 1}` : ""}`;
}

export function SourcePills({ sources, note, docs, laws }: { sources: string[]; note: string | null; docs: DocRef[]; laws: LawRef[] }) {
  if (!sources.length && !note) return null;
  const pill = "inline-flex max-w-full items-center rounded-full border px-2 py-0.5 text-xs font-semibold";
  return (
    <div className="mt-2 border-t border-line pt-2">
      {sources.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label="Quellen">
          {sources.map((s) => {
            const href = docHref(s, docs) ?? lawHref(s, laws) ?? brochureHref(s);
            return (
              <li key={s} className="max-w-full">
                {href ? (
                  <a
                    href={href}
                    {...(href.startsWith("/bff/") ? { target: "_blank", rel: "noreferrer" } : {})}
                    className={`${pill} border-accent/30 bg-accent-soft text-accent-strong hover:border-accent hover:underline`}
                    title={`Quelle öffnen: ${s}`}
                  >
                    <span className="truncate">{s}</span>
                  </a>
                ) : (
                  <span className={`${pill} border-line bg-surface text-muted`} title={s}>
                    <span className="truncate">{s}</span>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {note && <p className="mt-1.5 text-xs text-muted">{note}</p>}
    </div>
  );
}

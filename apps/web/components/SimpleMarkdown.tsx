/** Minimal, injection-safe rendering of the agent's replies: paragraphs, "- " lists (also mixed into a paragraph
 *  block), **bold** and `code` (shown as plain emphasis). No HTML is interpreted. */
export function SimpleMarkdown({ text }: { text: string }) {
  const blocks = text.trim().split(/\n{2,}/);
  return (
    <div className="space-y-2">
      {blocks.flatMap((block, i) => groups(block.split("\n")).map((g, j) => render(g, `${i}-${j}`)))}
    </div>
  );
}

type Group = { list: boolean; lines: string[] };
const BULLET = /^\s*[-*•]\s+/;

/** Split a block into consecutive runs of list lines and text lines. */
function groups(lines: string[]): Group[] {
  const out: Group[] = [];
  for (const l of lines) {
    const list = BULLET.test(l);
    const last = out[out.length - 1];
    if (last && last.list === list) last.lines.push(l);
    else out.push({ list, lines: [l] });
  }
  return out;
}

function render(g: Group, key: string) {
  if (g.list) {
    return (
      <ul key={key} className="list-disc space-y-0.5 pl-5">
        {g.lines.map((l, j) => (
          <li key={j}>{inline(l.replace(BULLET, ""))}</li>
        ))}
      </ul>
    );
  }
  return (
    <p key={key}>
      {g.lines.map((l, j) => (
        <span key={j}>
          {j > 0 && <br />}
          {inline(l)}
        </span>
      ))}
    </p>
  );
}

function inline(s: string) {
  // A single "*" inside bold is text (German gender star: "Rollstuhlfahrer*in"); only "**" ends the bold run.
  return s.split(/(\*\*(?:[^*]|\*(?!\*))+\*\*|`[^`]+`)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <span key={i} className="font-medium">{part.slice(1, -1)}</span>;
    return part;
  });
}

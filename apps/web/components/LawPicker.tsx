"use client";
// Law + paragraph pickers. Paragraphs come from GET /api/legal/laws/{key}/paragraphs; without that endpoint the
// § field falls back to free text.
import { useEffect, useState } from "react";
import { bff } from "@/lib/client";
import { type Law, type LawParagraph, linkableParagraphs } from "@/lib/laws";
import { Picker } from "./Picker";


export function LawPicker({ laws, defaultKey, defaultNr }: { laws: Law[]; defaultKey?: string; defaultNr?: string }) {
  const [law, setLaw] = useState(defaultKey ?? "");
  const [nr, setNr] = useState(defaultNr ?? "");
  const [paras, setParas] = useState<LawParagraph[] | null>(null);

  useEffect(() => {
    setParas(null);
    if (!law) return;
    let alive = true;
    bff<LawParagraph[]>(`/api/legal/laws/${encodeURIComponent(law)}/paragraphs`).then((r) => alive && setParas(r.ok ? linkableParagraphs(r.data) : []));
    return () => {
      alive = false;
    };
  }, [law]);

  return (
    <>
      <Picker
        name="law"
        label="Gesetz / Richtlinie"
        emptyLabel="Alle Gesetze"
        value={law}
        onChange={(v) => {
          setLaw(v);
          setNr("");
        }}
        options={laws.map((l) => ({
          value: l.key,
          label: l.abbr,
          sub: `${l.title}${l.paragraphs ? ` · ${l.paragraphs} Bestimmungen` : ""}`,
          search: l.key,
        }))}
      />
      {law && paras && paras.length > 0 ? (
        <Picker
          name="nr"
          label="§"
          emptyLabel="Alle Paragrafen"
          value={nr}
          onChange={setNr}
          options={paras.map((p) => ({ value: p.nr, label: p.label, sub: p.heading || undefined, search: p.nr }))}
        />
      ) : (
        <label className="flex flex-col gap-1">
          <span className="font-semibold">§</span>
          <input name="nr" value={nr} onChange={(e) => setNr(e.target.value)} className="input" placeholder={law ? "z. B. 4" : "erst Gesetz wählen"} disabled={!law} />
        </label>
      )}
    </>
  );
}

// Same-origin proxy for client components: forwards to the FastAPI backend with the
// user's token + subject from httpOnly cookies. Passes binary bodies (PDF, multipart) through.
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import { API_URL, COOKIE_SUBJECT, COOKIE_TOKEN } from "@/lib/session";

async function forward(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const jar = await cookies();
  const headers = new Headers({ "X-Via": "ui" });
  const token = jar.get(COOKIE_TOKEN)?.value;
  const subject = jar.get(COOKIE_SUBJECT)?.value;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (subject) headers.set("X-Subject-Id", subject);
  const ct = req.headers.get("content-type");
  if (ct) headers.set("Content-Type", ct);

  const hasBody = !["GET", "HEAD"].includes(req.method);
  const query = new URLSearchParams(req.nextUrl.search);
  const view = query.get("view") === "1";
  query.delete("view");
  const qs = query.toString() ? `?${query}` : "";
  const upstream = await fetch(`${API_URL}/${path.map(encodeURIComponent).join("/")}${qs}`, {
    method: req.method,
    headers,
    body: hasBody ? await req.arrayBuffer() : undefined,
    cache: "no-store",
  }).catch(() => null);
  if (!upstream) return Response.json({ detail: "Der Dienst ist gerade nicht erreichbar." }, { status: 502 });

  const out = new Headers();
  for (const h of ["content-type", "content-disposition"]) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  // Source view: display the PDF in the page (iframe) instead of downloading it.
  if (view) out.set("content-disposition", (out.get("content-disposition") ?? "inline").replace(/^attachment/, "inline"));
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH, forward as DELETE };

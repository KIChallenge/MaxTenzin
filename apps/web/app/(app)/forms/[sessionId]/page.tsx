import { ApiError } from "@/components/ApiError";
import { api } from "@/lib/api";
import { fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { FormDefinition, FormSession } from "@/lib/types";
import { Wizard } from "./Wizard";

export default async function FormPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const me = await getMe();
  const name = me.ok ? fullName(me.data.subject) : "";
  const s = await api<FormSession>(`/api/forms/sessions/${encodeURIComponent(sessionId)}`);
  if (!s.ok) return <ApiError status={s.status} detail={s.detail} subjectName={name} />;
  const d = await api<FormDefinition>(`/api/forms/definitions/${encodeURIComponent(s.data.form_id)}`);
  if (!d.ok) return <ApiError status={d.status} detail={d.detail} subjectName={name} />;
  return <Wizard definition={d.data} initial={s.data} subjectName={name} />;
}

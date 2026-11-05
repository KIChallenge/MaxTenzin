"use client";

export type OpenChatDetail = { question?: string; send?: boolean; fresh?: boolean };

/** Open Lotsi in a NEW conversation and send the question right away. */
export function askLotsi(question: string) {
  window.dispatchEvent(new CustomEvent<OpenChatDetail>("lotse:open-chat", { detail: { question, send: true, fresh: true } }));
}

export function OpenChatButton({ question, children, className, send = false }: { question?: string; children: React.ReactNode; className?: string; send?: boolean }) {
  return (
    <button
      type="button"
      className={className ?? "btn-primary"}
      onClick={() => window.dispatchEvent(new CustomEvent<OpenChatDetail>("lotse:open-chat", { detail: { question, send, fresh: send } }))}
    >
      {children}
    </button>
  );
}

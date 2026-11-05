"use client";
export function OpenChatButton({ question, children, className }: { question?: string; children: React.ReactNode; className?: string }) {
  return (
    <button
      type="button"
      className={className ?? "btn-primary"}
      onClick={() => window.dispatchEvent(new CustomEvent("lotse:open-chat", { detail: question }))}
    >
      {children}
    </button>
  );
}

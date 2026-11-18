"use client";

import { useId, type ReactNode } from "react";
import { X } from "lucide-react";

export function Sheet({
  label,
  title,
  trigger,
  children,
  className,
}: {
  label: string;
  title: string;
  trigger: ReactNode;
  children: (close: () => void) => ReactNode;
  className?: string;
}) {
  const dialogId = useId();
  function dialog() {
    const element = document.getElementById(dialogId);
    return element instanceof HTMLDialogElement ? element : null;
  }
  const titleId = useId();
  const close = () => dialog()?.close();
  return (
    <div className={className}>
      <button
        className="button button-secondary"
        type="button"
        aria-label={label}
        aria-haspopup="dialog"
        onClick={() => dialog()?.showModal()}
      >
        {trigger}
      </button>
      <dialog
        id={dialogId}
        className="sheet"
        aria-labelledby={titleId}
        onClick={(event) => {
          if (event.target === event.currentTarget) close();
        }}
      >
        <div className="sheet-content">
          <div className="sheet-title">
            <h2 id={titleId}>{title}</h2>
            <button
              className="icon-button"
              type="button"
              aria-label="Close dialog"
              onClick={close}
            >
              <X size={20} />
            </button>
          </div>
          {children(close)}
        </div>
      </dialog>
    </div>
  );
}

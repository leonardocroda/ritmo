"use client";

import { useEffect } from "react";

type RecalibrateModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export default function RecalibrateModal({ isOpen, onClose }: RecalibrateModalProps) {
  // Fecha ao pressionar Escape
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Recalibrar VDOT"
    >
      <div
        className="w-full max-w-md mx-4 bg-background rounded-card border border-border overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="font-semibold">Recalibrar VDOT</h2>
        </div>

        {/* Conteúdo */}
        <div className="p-4 space-y-4">
          <p className="text-sm text-muted">
            Para atualizar seu VDOT e zonas de ritmo, execute o comando abaixo no
            terminal do servidor onde o backend roda:
          </p>

          <div className="bg-muted/50 rounded-md p-3 font-mono text-sm overflow-x-auto">
            <code>python calibrate_vdot.py</code>
          </div>

          <p className="text-sm text-muted">
            O script fará uma entrevista interativa pedindo a distância e o tempo
            do seu último teste máximo. As zonas serão recalculadas e salvas no
            banco de dados (e mantidas no arquivo JSON para compatibilidade).
          </p>

          <div className="border-t border-border pt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded-md bg-muted hover:bg-muted/80 transition-colors"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
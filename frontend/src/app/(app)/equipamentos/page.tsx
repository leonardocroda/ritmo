"use client";

import ShoesSection from "@/components/workouts/ShoesSection";

// /equipamentos — gestão de tênis (MVP: só tênis; extensível para outros gear).
// Página client no padrão do /perfil: carrega a seção de tênis que já
// encapsula todo o estado (fetch, create, edit, retire, empty, error).

export default function EquipamentosPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6 pb-20">
      <h1 className="text-2xl font-semibold tracking-tight">Equipamentos</h1>
      <ShoesSection />
    </main>
  );
}
import { redirect } from "next/navigation";

// A home é o painel Treinos (decisão do spec workouts-list): redirect
// server-side, sem landing intermediária.
export default function Home() {
  redirect("/treinos");
}

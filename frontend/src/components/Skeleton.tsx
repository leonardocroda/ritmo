// Skeleton (DSN-23): bloco neutro pulsando ~1,6s — o carregamento na
// linguagem v0.3, sem spinner. A classe `skeleton` (keyframes no
// globals.css) carrega a animação e o gradiente raised→deep; a
// composição (tamanho e raio) vem do className de cada painel — o
// default cobre uma linha de texto.

export default function Skeleton({
  className = "h-4 w-2/3 rounded-ctl",
}: {
  className?: string;
}) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

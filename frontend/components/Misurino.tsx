/**
 * IL MISURINO — il pieno sotto la cifra, alto 3px.
 *
 * LINGUAGGIO A: la probabilità è un PIENO. Il riempimento è largo quanto la
 * probabilità, e la sua sola funzione è dare alla colonna della cifra una
 * seconda lettura, non numerica, che si coglie mentre si scorre.
 *
 * In v3 questo elemento portava anche la banda di incertezza, disegnata come
 * due grazie sopra il pieno. Le due marche si toccavano — un pieno e un
 * tratto sovrapposti in 5px — e a quella scala il tratto si leggeva come un
 * difetto del pieno. In v4 la banda ha la propria colonna (`<Affidabilita />`)
 * e qui resta solo il pieno: una marca, un significato.
 *
 * `aria-hidden`: la cifra qui accanto dice già il numero, e la definizione
 * operativa completa sta sulla scheda.
 */
export function Misurino({ p }: { p: number }) {
  return (
    <span className="misurino" aria-hidden="true">
      <span className="misurino__pieno" style={{ width: `${(p * 100).toFixed(1)}%` }} />
    </span>
  );
}

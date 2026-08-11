/**
 * IL MISURINO — il pieno sotto la cifra, alto 4px.
 *
 * La probabilità è un PIENO: il riempimento è largo quanto la probabilità, e
 * dà alla colonna della cifra una seconda lettura, non numerica, che si coglie
 * mentre si scorre.
 *
 * LA TACCA — l'elemento firma alla sua scala più piccola e più utile. Quando
 * conosciamo il prezzo di mercato, un quadretto vermiglio segna dove sta la
 * probabilità implicita in quella quota. La DISTANZA fra il riempimento e la
 * tacca è il vantaggio, e si vede senza leggere un numero:
 *
 *   pieno oltre la tacca  →  noi diamo più probabilità di quanta ne prezzi il
 *                            mercato: il prezzo è generoso
 *   tacca oltre il pieno  →  il mercato è più ottimista di noi: il prezzo è caro
 *
 * La tacca non porta mai un'etichetta numerica: il prezzo è lordo, quindi
 * `1/prezzo` sovrastima un po' la probabilità vera del mercato. È un
 * riferimento visivo, e presentarlo come misura sarebbe una precisione finta.
 *
 * `aria-hidden`: la cifra qui accanto dice già il numero, e la scheda porta il
 * confronto in parole per intero.
 */
export function Misurino({ p, mercato = null }: { p: number; mercato?: number | null }) {
  return (
    <span className="misurino" aria-hidden="true">
      <span className="misurino__pieno" style={{ width: `${(p * 100).toFixed(1)}%` }} />
      {mercato !== null ? (
        <span className="misurino__tacca" style={{ left: `${(mercato * 100).toFixed(1)}%` }} />
      ) : null}
    </span>
  );
}

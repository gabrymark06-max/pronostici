/**
 * L'AVVISO SU OVER/UNDER — il debito che paga la riammissione di questa famiglia.
 *
 * Il backtest su 5.018 partite ha misurato che sui GOL TOTALI il nostro modello
 * non batte la semplice frequenza storica del campionato: log loss 0,69919
 * contro 0,68856. Sette configurazioni dichiarate hanno escluso l'emivita, la
 * correzione di Dixon-Coles e il troncamento della matrice. Su quel mercato
 * l'informazione non c'è, e per tre giorni over/under è stato calcolato e
 * mostrato ma mai consigliato.
 *
 * Il 12 agosto 2026 il proprietario ha chiesto che tornasse consigliabile,
 * conoscendo questo risultato. È una sua decisione ed è stata eseguita. Ma un
 * sito che si presenta dicendo «ci facciamo misurare in pubblico» non può
 * pubblicare un consiglio che i suoi stessi numeri smentiscono senza dirlo
 * ACCANTO al consiglio: non in una pagina di note, non in fondo, non in un
 * asterisco. Qui, sotto il numero, dove chi legge quel numero lo vede.
 *
 * Compare su ogni pronostico della famiglia `over_under`, in lista e sulla
 * scheda. Se un backtest futuro su più dati ribaltasse la misura, questo
 * componente sparisce e il registro dei parametri lo data.
 */
export function AvvisoOverUnder({ compatto = false }: { compatto?: boolean }) {
  if (compatto) {
    return (
      <span className="avviso avviso--riga">
        <span aria-hidden="true">!</span> nessun vantaggio dimostrato su questo mercato
      </span>
    );
  }

  return (
    <p className="avviso">
      <span className="avviso__marca" aria-hidden="true">
        !
      </span>
      <span>
        <strong>Su questo mercato non abbiamo dimostrato un vantaggio.</strong> Il nostro
        test storico su 5.018 partite dice che sui gol totali il modello non fa meglio
        della semplice media del campionato. Lo consigliamo su richiesta esplicita del
        proprietario del sito, e te lo diciamo qui invece che in fondo alla pagina.
      </span>
    </p>
  );
}

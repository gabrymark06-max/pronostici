"""Un limitatore di tentativi, a finestra scorrevole.

A COSA SERVE DAVVERO: senza, `/accesso` e' un oracolo che risponde «si'/no» a
mille password al secondo, e nessuna regola sulla lunghezza salva un utente da
un dizionario provato per intero. Con otto tentativi ogni quindici minuti per
coppia (indirizzo, email) un attacco che prima durava un'ora dura anni.

LA CHIAVE E' (INDIRIZZO, EMAIL) E NON SOLO L'INDIRIZZO. Solo l'indirizzo
punirebbe tutti quelli dietro lo stesso NAT aziendale per colpa di uno; solo
l'email permetterebbe a una botnet di provare la stessa casella da mille
indirizzi. Insieme reggono i due casi.

STA IN MEMORIA, E QUESTO E' UN LIMITE DICHIARATO. Con piu' di un processo ogni
processo ha il suo profilo, e i tentativi effettivi si moltiplicano per il numero
di processi. Va bene per un'istanza sola — che e' come parte questo servizio —
e quando ne servira' una seconda questo modulo va spostato su Redis. E' scritto
qui e non in un file di cose da fare perche' e' qui che verra' letto.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class Limitatore:
    def __init__(self, tentativi: int, finestra_s: int) -> None:
        self.tentativi = tentativi
        self.finestra_s = finestra_s
        self._storia: dict[str, deque[float]] = defaultdict(deque)

    def _pulisci(self, chiave: str, adesso: float) -> deque[float]:
        coda = self._storia[chiave]
        limite = adesso - self.finestra_s
        while coda and coda[0] < limite:
            coda.popleft()
        return coda

    def consentito(self, chiave: str) -> tuple[bool, int]:
        """`(passa, fra quanti secondi si riprova)`.

        NON registra il tentativo: lo fa `segna()`, e solo sui tentativi
        FALLITI. Chi indovina la password al primo colpo non deve consumare
        niente, e chi rientra dieci volte in un pomeriggio non deve trovarsi
        chiuso fuori.
        """
        adesso = time.monotonic()
        coda = self._pulisci(chiave, adesso)
        if len(coda) < self.tentativi:
            return True, 0
        attesa = int(self.finestra_s - (adesso - coda[0])) + 1
        return False, max(attesa, 1)

    def segna(self, chiave: str) -> None:
        self._storia[chiave].append(time.monotonic())

    def azzera(self, chiave: str) -> None:
        """Dopo un accesso riuscito. I tentativi andati male prima non devono
        pesare sul prossimo giro."""
        self._storia.pop(chiave, None)

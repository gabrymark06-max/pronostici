"""La traduzione delle quote Sofascore nelle nostre chiavi.

Il pezzo delicato non e' la mappatura dei nomi — quella o c'e' o non c'e' — ma
lo SGONFIAMENTO: dividere per la somma delle probabilita' implicite toglie il
margine solo se quella somma ha il bersaglio giusto. Sulla doppia chance il
bersaglio e' 2, e sbagliarlo non produceva numeri storti: produceva il silenzio,
che e' un guasto molto piu' difficile da notare.
"""


def test_doppia_chance_e_una_copertura_doppia():
    """La doppia chance somma a 2, non a 1, e va sgonfiata su quel bersaglio.

    Il controllo di plausibilita' con la fascia fissa 0,9-1,6 la scartava
    sempre: 1X + X2 + 12 valgono per costruzione due volte lo spazio degli
    esiti, quindi la loro somma equa e' 2 e con il margine sfiora 2,1. La
    famiglia piu' popolata della tavola restava senza quote per un controllo
    tarato su un'altra forma di mercato.
    """
    from pronostici.jobs.sofascore import _market_p

    quote = {
        "mercati": [
            {
                "mercato": "Double chance",
                "esiti": [
                    {"esito": "1X", "probabilita_implicita": 0.9434},
                    {"esito": "X2", "probabilita_implicita": 0.2667},
                    {"esito": "12", "probabilita_implicita": 0.8850},
                ],
            }
        ]
    }
    fuori = _market_p(quote)
    assert set(fuori) == {"dc_1x", "dc_x2", "dc_12"}
    # Sgonfiate, le tre coprono lo spazio esattamente due volte.
    assert abs(sum(fuori.values()) - 2.0) < 1e-4
    # E restano nell'ordine di grandezza dei prezzi da cui vengono.
    assert 0.88 < fuori["dc_1x"] < 0.92


def test_linee_gol_oltre_il_catalogo_restano_fuori():
    """Sofascore arriva a 8,5; il nostro catalogo si ferma a 4,5.

    Una chiave `over_8.5` non avrebbe un nostro numero accanto a cui stare, e
    riempirebbe la tavola di righe che nessuno puo' confrontare.
    """
    from pronostici.jobs.sofascore import _market_p

    def gol(linea):
        return {
            "mercato": "Match goals",
            "linea": linea,
            "esiti": [
                {"esito": "Over", "probabilita_implicita": 0.55},
                {"esito": "Under", "probabilita_implicita": 0.50},
            ],
        }

    fuori = _market_p({"mercati": [gol("4.5"), gol("8.5")]})
    assert "over_4.5" in fuori
    assert not any(k.endswith("8.5") for k in fuori)

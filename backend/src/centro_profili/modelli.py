"""Le tabelle. Due, e non una.

`utenti` e' ovvia. `sessioni` esiste per una ragione precisa: senza, «esci» non
esce da niente.

IL PROBLEMA DEI GETTONI FIRMATI. Un JWT e' valido perche' la firma torna, non
perche' il server dica di si': una volta emesso vale fino alla scadenza, e
cancellare il cookie lo toglie solo dal browser che l'ha chiesto. Chi l'avesse
copiato continua a entrare. «Esci da tutti i dispositivi» sarebbe impossibile,
e cambiare la password non caccerebbe fuori nessuno.

Con questa tabella il gettone di rinnovo porta un identificativo (`jti`) che
qui dentro puo' essere REVOCATO. Il gettone d'accesso resta corto — quindici
minuti — e quella e' la finestra massima in cui un accesso revocato sopravvive.
E' il compromesso solito, ed e' scritto qui perche' sia una scelta e non una
dimenticanza.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Utente(Base):
    __tablename__ = "utenti"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # L'EMAIL SI CONSERVA NORMALIZZATA (minuscola, senza spazi ai lati) e con
    # un vincolo di unicita' del database, non solo un controllo prima
    # dell'inserimento: fra il controllo e la scrittura c'e' spazio per due
    # registrazioni simultanee, e a decidere chi vince dev'essere il database.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    hash_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Sempre `False` oggi: verificare un'email richiede spedirla, e spedirla
    # richiede un servizio di posta che questo progetto non ha ancora. Il campo
    # esiste gia' perche' il giorno in cui si incassa serve — non si vende
    # niente a un indirizzo che nessuno ha confermato — e aggiungerlo dopo
    # significherebbe una migrazione su una tabella piena.
    email_verificata: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attivo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    creato: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ultimo_accesso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # LA GENERAZIONE DELLE CREDENZIALI.
    #
    # Revocare una sessione toglie il gettone di RINNOVO, ma quello d'ACCESSO
    # e' firmato e vale fino alla scadenza: cambiando password gli altri
    # browser restavano dentro fino a quindici minuti. Misurato con un browser
    # vero, non dedotto — la prova su HTTP diretto non lo vedeva, perche' non
    # riusava il gettone d'accesso di prima.
    #
    # Quindici minuti sono pochi in astratto e sono tantissimi nel momento in
    # cui uno cambia la password: lo fa perche' pensa che qualcuno sia entrato,
    # e quel qualcuno continuerebbe a leggere.
    #
    # Ogni gettone porta la generazione con cui e' stato coniato. Cambiare
    # password, o uscire da tutti i dispositivi, la incrementa: tutti i gettoni
    # con la generazione vecchia smettono di valere all'istante. Costa zero
    # query — l'utente e' gia' caricato per gli altri controlli.
    #
    # UN CONTATORE E NON UNA DATA, e il primo tentativo era una data. Il
    # confronto fra `iat` — che JWT definisce in secondi interi — e un istante
    # non distingue due eventi dentro lo stesso secondo: il gettone coniato
    # subito prima del cambio password risultava ancora valido, ed e' proprio
    # il caso che questa colonna deve fermare. Un intero non ha risoluzione,
    # quindi non ha questo problema.
    generazione: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    sessioni: Mapped[list[Sessione]] = relationship(
        back_populates="utente", cascade="all, delete-orphan"
    )


class Sessione(Base):
    """Un gettone di rinnovo vivo. Sparisce quando si esce o quando scade."""

    __tablename__ = "sessioni"

    # E' il `jti` del gettone di rinnovo: il gettone non si conserva mai, ne'
    # in chiaro ne' cifrato. Qui c'e' solo il suo identificativo, che da solo
    # non permette di entrare.
    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)

    utente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("utenti.id", ondelete="CASCADE"), index=True
    )
    creata: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    scade: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # A che cosa somigliava il browser che ha aperto la sessione. Serve alla
    # pagina «dove sei collegato», e si tronca a 200 caratteri perche' oltre
    # non dice niente di piu'.
    agente: Mapped[str | None] = mapped_column(String(200), nullable=True)

    utente: Mapped[Utente] = relationship(back_populates="sessioni")


class GettoneEmail(Base):
    """Un gettone spedito per posta: conferma dell'indirizzo, o recupero password.

    NON SI CONSERVA IL GETTONE, SI CONSERVA IL SUO HASH. Vale la stessa ragione
    delle password: chi leggesse questa tabella — una copia di sicurezza finita
    nel posto sbagliato, un accesso al database — potrebbe altrimenti prendere
    il gettone di recupero di chiunque e cambiargli la password. Con l'hash non
    ci fa niente.

    E' SHA-256 E NON ARGON2, e non e' una svista. Argon2 e' lento apposta,
    perche' le password sono corte e indovinabili. Questi gettoni sono 32 byte
    casuali: non esiste dizionario che li contenga, non c'e' niente da
    rallentare, e un hash lento qui vorrebbe dire mezzo secondo di CPU su ogni
    clic in un'email.

    UNA RIGA PER TIPO, PER UTENTE. Chiedere un secondo recupero cancella il
    primo: due collegamenti vivi contemporaneamente raddoppiano la finestra in
    cui uno rubato funziona, e non servono a niente.
    """

    __tablename__ = "gettoni_email"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    utente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("utenti.id", ondelete="CASCADE"), index=True
    )
    # `verifica` oppure `recupero`.
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    impronta: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    creato: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    scade: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

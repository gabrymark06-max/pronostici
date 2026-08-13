"""Utenti e sessioni.

Revision ID: 0001
Revises:
Create Date: 2026-08-13

Scritta a mano e non generata con `--autogenerate`, perche' e' la prima: su un
database vuoto l'autogenerazione non ha niente da confrontare, e quello che
produce va comunque riletto riga per riga. Dalla seconda in poi si genera.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "utenti",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # 320 e' il massimo di un indirizzo di posta secondo la RFC 5321:
        # 64 di parte locale + @ + 255 di dominio.
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("hash_password", sa.String(255), nullable=False),
        sa.Column(
            "email_verificata", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("attivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "creato", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ultimo_accesso", sa.DateTime(timezone=True), nullable=True),
        # Vedi il commento in `modelli.py`: i gettoni con una generazione
        # vecchia non valgono piu'. Aggiunta a questa migrazione e non a una
        # seconda perche' la 0001 non e' mai stata applicata da nessuna parte:
        # dal primo deploy in poi ogni cambio di schema fa la sua.
        sa.Column("generazione", sa.Integer(), nullable=False, server_default="0"),
    )
    # L'unicita' e' un VINCOLO del database e non un controllo applicativo: fra
    # la SELECT che verifica e la INSERT che scrive c'e' spazio perche' due
    # registrazioni simultanee passino entrambe. Qui a decidere e' Postgres.
    op.create_index("ix_utenti_email", "utenti", ["email"], unique=True)

    op.create_table(
        "sessioni",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "utente_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("utenti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "creata", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("scade", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agente", sa.String(200), nullable=True),
    )
    op.create_index("ix_sessioni_utente_id", "sessioni", ["utente_id"])
    # Le sessioni scadute si cancellano a lotti; senza indice quella pulizia
    # scansiona tutta la tabella, che e' la piu' grande delle due.
    op.create_index("ix_sessioni_scade", "sessioni", ["scade"])


def downgrade() -> None:
    op.drop_index("ix_sessioni_scade", table_name="sessioni")
    op.drop_index("ix_sessioni_utente_id", table_name="sessioni")
    op.drop_table("sessioni")
    op.drop_index("ix_utenti_email", table_name="utenti")
    op.drop_table("utenti")

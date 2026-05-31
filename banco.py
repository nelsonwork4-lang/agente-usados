# ============================================================
# banco.py — SQLite para persistência dos anúncios avaliados
# ============================================================

import sqlite3
from datetime import datetime

DB = "usados.db"


def criar_tabelas():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS anuncios (
                id_facebook   TEXT PRIMARY KEY,
                titulo        TEXT,
                preco         REAL,
                preco_ref     REAL,
                desconto      REAL,
                categoria     TEXT,
                score         INTEGER,
                recomendacao  TEXT,
                link          TEXT,
                avaliado_em   TEXT
            )
        """)
        con.commit()


def ja_avaliado(id_fb):
    with sqlite3.connect(DB) as con:
        r = con.execute("SELECT 1 FROM anuncios WHERE id_facebook=?", (id_fb,)).fetchone()
        return r is not None


def salvar(av):
    with sqlite3.connect(DB) as con:
        con.execute("""
            INSERT OR REPLACE INTO anuncios
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            av.get("id_facebook",""),
            av.get("titulo",""),
            av.get("preco",0),
            av.get("preco_ref",0),
            av.get("desconto",0),
            av.get("categoria",""),
            av.get("score",0),
            av.get("recomendacao",""),
            av.get("link",""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        con.commit()


def total_avaliados():
    with sqlite3.connect(DB) as con:
        return con.execute("SELECT COUNT(*) FROM anuncios").fetchone()[0]

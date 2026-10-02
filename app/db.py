"""Acceso a SQLite. Todo se guarda en DATA_DIR/menu.db (volumen Docker)."""
import json
import sqlite3
import threading
from contextlib import contextmanager

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    title TEXT,
    source_url TEXT,
    source_id TEXT,
    pdf_file TEXT,
    parser TEXT,
    raw_text TEXT,
    fetched_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(year, month)
);

-- Lo que comen los niños en el cole cada día lectivo
CREATE TABLE IF NOT EXISTS school_days (
    date TEXT PRIMARY KEY,            -- YYYY-MM-DD
    dishes TEXT NOT NULL DEFAULT '[]',-- JSON: ["Lentejas con verduras", "Merluza...", "Fruta"]
    dinner_hint TEXT DEFAULT '',      -- recomendación de cena del PDF (puede ser solo ingredientes)
    note TEXT DEFAULT '',             -- festivo, menú especial...
    edited INTEGER DEFAULT 0
);

-- Comidas y cenas que se hacen en casa (cenas entre semana, comidas y cenas del finde)
CREATE TABLE IF NOT EXISTS plan (
    date TEXT NOT NULL,
    meal TEXT NOT NULL,               -- 'comida' | 'cena'
    options TEXT NOT NULL DEFAULT '[]',  -- JSON: lista de platos recomendados
    choice TEXT,                      -- JSON: plato elegido {name, ingredients, groups}
    edited INTEGER DEFAULT 0,
    PRIMARY KEY (date, meal)
);

CREATE TABLE IF NOT EXISTS shopping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week TEXT NOT NULL,               -- lunes de la semana YYYY-MM-DD
    name TEXT NOT NULL,
    qty TEXT DEFAULT '',
    section TEXT DEFAULT 'Otros',
    checked INTEGER DEFAULT 0,
    manual INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0,
    UNIQUE(week, name)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Gasto de IA por mes (para el límite mensual)
CREATE TABLE IF NOT EXISTS ai_usage (
    month TEXT PRIMARY KEY,           -- YYYY-MM
    cost REAL DEFAULT 0,
    calls INTEGER DEFAULT 0,
    images INTEGER DEFAULT 0
);

-- Platos creados por la IA: se reutilizan gratis la próxima vez
CREATE TABLE IF NOT EXISTS library (
    key TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created TEXT DEFAULT (datetime('now','localtime'))
);

-- Fotos de platos (una por nombre normalizado)
CREATE TABLE IF NOT EXISTS photos (
    key TEXT PRIMARY KEY,
    name TEXT,
    file TEXT,
    status TEXT DEFAULT 'pending',    -- pending | ok | error
    created TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT DEFAULT (datetime('now','localtime')),
    level TEXT,
    message TEXT
);
"""


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def tx():
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init():
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    config.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with tx() as c:
        c.executescript(SCHEMA)


def log(level: str, message: str):
    try:
        with tx() as c:
            c.execute("INSERT INTO log(level, message) VALUES (?,?)", (level, message[:2000]))
            c.execute("DELETE FROM log WHERE id NOT IN (SELECT id FROM log ORDER BY id DESC LIMIT 200)")
    except Exception:
        pass
    print(f"[{level}] {message}", flush=True)


def loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def get_setting(key, default=None):
    with tx() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with tx() as c:
        c.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

# memory.py — память: история диалога + факты о тебе (SQLite, переживает перезапуск)
import sqlite3, os, time, threading

class Memory:
    def __init__(self, path="memory/assistant.db"):
        os.makedirs("memory", exist_ok=True)
        self.lock = threading.RLock()
        with self.lock:
            self.conn = sqlite3.connect(path, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA busy_timeout=5000")
            self.conn.execute("CREATE TABLE IF NOT EXISTS messages (role TEXT, content TEXT, ts REAL, source TEXT, emotion TEXT)")
            # Индекс для ускорения выборки истории
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts)")
            # Миграция старой схемы если колонок source / emotion ещё нет
            try:
                self.conn.execute("ALTER TABLE messages ADD COLUMN source TEXT DEFAULT 'other'")
            except Exception:
                pass
            try:
                self.conn.execute("ALTER TABLE messages ADD COLUMN emotion TEXT DEFAULT ''")
            except Exception:
                pass
            self.conn.execute("CREATE TABLE IF NOT EXISTS facts (fact TEXT, ts REAL)")
            self.conn.commit()

    def add_message(self, role, content, source="other", emotion=""):
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO messages (role, content, ts, source, emotion) VALUES (?,?,?,?,?)",
                (role, content, time.time(), source, emotion or "")
            )
            self.conn.commit()
            return cur.lastrowid

    def recent_messages(self, limit=20):
        """Возвращает контекст для промпта LLM."""
        with self.lock:
            rows = self.conn.execute(
                "SELECT role, content FROM messages ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def recent_dialog(self, limit=60, since_id=0):
        """Возвращает полную историю с источниками (voice, telegram, web) для веб-панели."""
        with self.lock:
            if since_id > 0:
                rows = self.conn.execute(
                    "SELECT rowid, role, content, ts, source, emotion FROM messages WHERE rowid > ? ORDER BY rowid ASC LIMIT ?",
                    (since_id, limit)
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT rowid, role, content, ts, source, emotion FROM messages ORDER BY rowid DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                rows = list(reversed(rows))

        out = []
        for rowid, role, content, ts, source, emotion in rows:
            out.append({
                "id": rowid,
                "role": role,
                "content": content,
                "ts": ts,
                "source": source or "other",
                "emotion": emotion or ""
            })
        return out

    def add_fact(self, fact):
        with self.lock:
            self.conn.execute("INSERT INTO facts VALUES (?,?)", (fact, time.time()))
            self.conn.commit()

    def all_facts(self):
        with self.lock:
            return [r[0] for r in self.conn.execute("SELECT fact FROM facts ORDER BY ts").fetchall()]
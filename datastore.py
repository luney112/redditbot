import sqlite3

BOT_DATA_STORE = 'botdata.db'


class SimpleDataStore(object):
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def open(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, *args, **kwargs):
        self.open()
        c = self.conn.cursor()
        c.execute(*args, **kwargs)
        return c

    def commit(self):
        if self.conn:
            self.conn.commit()


class BotDataStore(object):
    def __init__(self, bot_name):
        self.bot_name = bot_name
        self.data_store = SimpleDataStore(BOT_DATA_STORE)
        self.create()

    def create(self):
        self.data_store.execute("""
            CREATE TABLE IF NOT EXISTS ignore (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                bot_name TEXT,
                target_name TEXT
               );
            """)

        self.data_store.execute("""
            CREATE TABLE IF NOT EXISTS xkcd_counter (
                id INTEGER NOT NULL PRIMARY KEY,
                count INTEGER
                );
            """)

        self.data_store.execute("""
            CREATE VIEW IF NOT EXISTS xkcd_stats AS
                SELECT
                    id,
                    count,
                    (count * 100.0) / (SELECT SUM(count) FROM xkcd_counter) AS percentage
                FROM
                    xkcd_counter
                ORDER BY
                    percentage DESC
                ;
            """)

        self.data_store.commit()

    def add_ignore(self, target):
        self.data_store.execute(
            'INSERT INTO ignore VALUES(null, ?, ?)',
            (self.bot_name, target)
        )

        self.data_store.commit()

    def get_ignores(self):
        cursor = self.data_store.execute(
            'SELECT target_name FROM ignore WHERE bot_name = ?',
            (self.bot_name,)
        )

        return [r[0] for r in cursor]

    def get_stats(self, comic_id):
        cursor = self.data_store.execute(
            'SELECT count, percentage FROM xkcd_stats WHERE id = ?',
            (comic_id,)
        )

        return cursor.fetchone()

    def increment_xkcd_count(self, comic_id):
        self.data_store.execute(
            'INSERT OR IGNORE INTO xkcd_counter VALUES(?, 0);',
            (int(comic_id),)
        )

        self.data_store.execute(
            'UPDATE xkcd_counter SET count = count + 1 WHERE id = ?',
            (int(comic_id),)
        )

        self.data_store.commit()

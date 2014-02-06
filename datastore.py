import sqlite3


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
    def __init__(self, bot_name, database_name):
        self.bot_name = bot_name
        self.database_name = database_name
        self.data_store = SimpleDataStore(self.database_name)
        self.create()

    def create(self):
        self.data_store.execute("""
            CREATE TABLE IF NOT EXISTS stats_ignore (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                bot_name TEXT,
                target_name TEXT
               );
            """)

        self.data_store.execute("""
            CREATE TABLE IF NOT EXISTS stats_xkcd_counter (
                id INTEGER NOT NULL PRIMARY KEY,
                count INTEGER
                );
            """)

        self.data_store.execute("""
            CREATE TABLE IF NOT EXISTS stats_xkcd_event (
                id INTEGER NOT NULL,
                time INTEGER NOT NULL,
                subreddit TEXT,
                user TEXT,
                link TEXT,
                from_external BOOLEAN
            );
            """)

        self.data_store.execute("""
            CREATE TABLE IF NOT EXISTS stats_xkcd_meta (
                id INTEGER PRIMARY KEY,
                json TEXT,
                hash_avg TEXT,
                hash_d TEXT,
                hash_p TEXT
            );
            """)

        self.data_store.execute("""
            CREATE VIEW IF NOT EXISTS stats_xkcd_stats AS
                SELECT
                    comic_id,
                    count,
                    (count * 100.0) / (SELECT SUM(count) FROM stats_xkcd_counter) AS percentage
                FROM
                    stats_xkcd_counter
                ORDER BY
                    percentage DESC
                ;
            """)

        self.data_store.commit()

    def add_ignore(self, target):
        self.data_store.execute(
            'INSERT INTO stats_ignore VALUES(null, ?, ?)',
            (self.bot_name, target)
        )

        self.data_store.commit()

    def get_ignores(self):
        cursor = self.data_store.execute(
            'SELECT target_name FROM stats_ignore WHERE bot_name = ?',
            (self.bot_name,)
        )

        return [r[0] for r in cursor]

    def get_stats(self, comic_id):
        cursor = self.data_store.execute(
            'SELECT count, percentage FROM stats_xkcd_stats WHERE comic_id = ?',
            (comic_id,)
        )

        return cursor.fetchone()

    def insert_xkcd_event(self, comic_id, time, subreddit, user, link, from_external):
        self.data_store.execute(
            'INSERT INTO stats_xkcd_event VALUES(null, ?, ?, ?, ?, ?, ?)',
            (comic_id, time, subreddit, user, link, from_external)
        )

        self.data_store.commit()

    def increment_xkcd_count(self, comic_id):
        r = self.data_store.execute(
            'SELECT 1 FROM stats_xkcd_counter WHERE comic_id = ?;',
            (int(comic_id),)
        )

        if r.fetchone() is None:
            self.data_store.execute(
                'INSERT INTO stats_xkcd_counter VALUES(null, ?, 0);',
                (int(comic_id),)
            )

        self.data_store.execute(
            'UPDATE stats_xkcd_counter SET count = count + 1 WHERE comic_id = ?',
            (int(comic_id),)
        )

        self.data_store.commit()

    def get_xkcd_meta(self, comic_id):
        cursor = self.data_store.execute(
            'SELECT * FROM stats_xkcd_meta WHERE id = ?;',
            (int(comic_id),)
        )

        return cursor.fetchone()

    def insert_xkcd_meta(self, comic_id, json, hash_avg, hash_d, hash_p):
        r = self.data_store.execute(
            'SELECT 1 FROM stats_xkcd_meta WHERE id = ?;',
            (int(comic_id),)
        )

        if r.fetchone() is None:
            self.data_store.execute(
                'INSERT INTO stats_xkcd_meta VALUES(?, ?, ?, ?, ?)',
                (int(comic_id), json, str(hash_avg), str(hash_d), str(hash_p))
            )

            self.data_store.commit()

    def close(self):
        try:
            self.data_store.close()
        except:
            pass

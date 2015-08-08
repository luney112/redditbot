import os
import sqlite3

import simplejson


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
    def __init__(self, bot_name, database_path):
        # Create the path if it does not alreay exist
        if not os.path.exists(os.path.dirname(database_path)):
            os.makedirs(os.path.dirname(database_path))

        self.bot_name = bot_name
        self.database_path = database_path
        self.datastore = SimpleDataStore(self.database_path)
        self.create()

    def create(self):
        self.datastore.execute("""
            CREATE TABLE IF NOT EXISTS ignored_users (
                bot_name TEXT,
                target_name TEXT,
                UNIQUE(bot_name, target_name) ON CONFLICT IGNORE
            );
            """)

        self.datastore.execute("""
            CREATE TABLE IF NOT EXISTS xkcd_comic_references (
                comic_id INTEGER,
                time INTEGER NOT NULL,
                subreddit TEXT,
                user TEXT,
                link TEXT,
                UNIQUE(comic_id, subreddit, user, link) ON CONFLICT IGNORE
            );
            """)

        self.datastore.execute("""
            CREATE TABLE IF NOT EXISTS xkcd_comic_meta (
                comic_id INTEGER PRIMARY KEY,
                json TEXT,
                title TEXT,
                hash_avg TEXT,
                hash_d TEXT,
                hash_p TEXT
            );
            """)

        self.datastore.execute("""
            CREATE VIEW IF NOT EXISTS references_counts AS
                SELECT
                    comic_id,
                    0 AS comic_count,
                    0.0 AS comic_percentage
                FROM
                    xkcd_comic_meta
                WHERE comic_id NOT IN (
                    SELECT DISTINCT(comic_id) FROM xkcd_comic_references
                )
                UNION
                SELECT
                    comic_id,
                    COUNT(*) AS comic_count,
                    (COUNT(*) * 100.0) / (SELECT COUNT(*) FROM xkcd_comic_references) AS comic_percentage
                FROM
                    xkcd_comic_references
                GROUP BY
                    comic_id
            ;
            """)

        self.datastore.commit()

    def add_ignore(self, target):
        self.datastore.execute(
            'INSERT INTO ignored_users VALUES(?, ?)',
            (self.bot_name, target)
        )

        self.datastore.commit()

    def get_ignores(self):
        cursor = self.datastore.execute(
            'SELECT target_name FROM ignored_users WHERE bot_name = ?',
            (self.bot_name,)
        )

        return [r[0] for r in cursor]

    def get_stats(self, comic_id):
        cursor = self.datastore.execute(
            'SELECT comic_count, comic_percentage FROM references_counts WHERE comic_id = ?',
            (int(comic_id),)
        )

        meta = cursor.fetchone()
        if not meta:
            return None
        return {
            'count': meta[0],
            'percentage': meta[1]
        }

    def insert_xkcd_event(self, comic_id, time, subreddit, user, link, from_external):
        self.datastore.execute(
            'INSERT INTO xkcd_comic_references VALUES(?, ?, ?, ?, ?)',
            (int(comic_id), int(time), subreddit, user, link)
        )

        self.datastore.commit()

    def get_xkcd_meta(self, comic_id):
        cursor = self.datastore.execute(
            'SELECT comic_id, json, hash_avg, hash_d, hash_p FROM xkcd_comic_meta WHERE comic_id = ?',
            (int(comic_id),)
        )

        meta = cursor.fetchone()
        if not meta:
            return None
        return {
            'comic_id': meta[0],
            'json_data': simplejson.loads(meta[1]),
            'hash_avg': meta[2],
            'hash_d': meta[3],
            'hash_p': meta[4],
        }

    def insert_xkcd_meta(self, comic_id, json, hash_avg, hash_d, hash_p):
        r = self.datastore.execute(
            'SELECT 1 FROM xkcd_comic_meta WHERE comic_id = ?',
            (int(comic_id),)
        )

        if r.fetchone() is None:
            self.datastore.execute(
                'INSERT INTO xkcd_comic_meta VALUES(?, ?, ?, ?, ?, ?)',
                (int(comic_id), simplejson.dumps(json), json.get('title', ''), str(hash_avg), str(hash_d), str(hash_p))
            )

            self.datastore.commit()

    def close(self):
        try:
            self.datastore.close()
        except Exception as e:
            pass

# Fetches xkcd data and takes the image hashes of them
# Only used to generate the initial data

from datastore import SimpleDataStore
from urllib import FancyURLopener
import simplejson as json
import urllib2
import Image
import imagehash

XKCD_JSON_API_URL = 'http://xkcd.com/{comic_id}/info.0.json'
DATA_STORE_PATH = '/home/jeremy/sites-prod/xkcdref/db.sqlite3'

data_store = SimpleDataStore(DATA_STORE_PATH)


class MyOpener(FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11'


def get_xkcd_json(comic_id):
    if int(comic_id) == 404:
        return {'title': '404', 'transcript': '404', 'alt': '404', 'img': ''}

    try:
        response = urllib2.urlopen(XKCD_JSON_API_URL.format(comic_id=comic_id))
        html = response.read()
        return json.loads(html)
    except:
        return None


data_store.execute("""
    CREATE TABLE IF NOT EXISTS stats_xkcd_meta (
        id INTEGER PRIMARY KEY,
        json TEXT,
        hash_avg TEXT,
        hash_d TEXT,
        hash_p TEXT
    );
    """)


myopener = MyOpener()
counter = 1
j = get_xkcd_json(counter)
while j is not None:
    if j.get('img'):
        myopener.retrieve(j.get('img'), 't')
        try:
            hash_avg = imagehash.average_hash(Image.open('t'))
            hash_d = imagehash.dhash(Image.open('t'))
            hash_p = imagehash.phash(Image.open('t'))
        except Exception as e:
            print e
            hash_avg = ''
            hash_d = ''
            hash_p = ''
            print 'Could not get image for', counter
    else:
        hash_avg = ''
        hash_d = ''
        hash_p = ''
        print 'Could not get image for', counter

    print 'Got', counter, hash_avg, hash_d, hash_p
    data_store.execute('INSERT INTO stats_xkcd_meta VALUES(?, ?, ?, ?, ?)',
                       (counter, json.dumps(j), str(hash_avg), str(hash_d), str(hash_p)))
    data_store.commit()
    counter += 1
    j = get_xkcd_json(counter)

data_store.commit()

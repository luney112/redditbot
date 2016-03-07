import urllib2
import re
import logging
import urlparse

import simplejson

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

XKCD_JSON_API_URL = 'http://xkcd.com/{comic_id}/info.0.json'
XKCD_EXPLAINED_URL = 'https://www.explainxkcd.com/wiki/index.php/{comic_id}#Explanation'


class XkcdFetcher(object):
    def __init__(self, datastore):
        self.datastore = datastore
        self.next_index = 1
        self.reverse_image_index = {}
        self.reverse_hash_index = {}
        self.json_index = {}

    def get_json(self, url):
        if not url.startswith('http'):
            url = '//' + url
        parsed = urlparse.urlparse(url)

        if re.match('^(www\.)?imgs\.xkcd\.com$', parsed.netloc.lower()):
            if parsed.path not in self.reverse_image_index:
                self._load_indexes()
            comic_id = self.reverse_image_index.get(parsed.path)
            return self.json_index.get(comic_id) if comic_id else None

        if re.match('^(www\.)?xkcd\.com$', parsed.netloc.lower()) and re.match('^/\d+/?$', parsed.path):
            m = re.search('^/(\d+)/?$', parsed.path)
            comic_id = int(m.group(1))
            if comic_id not in self.json_index:
                self._load_indexes()
            return self.json_index.get(comic_id) if comic_id else None

        if re.match('^imgur\.com$', parsed.netloc):
            pass

        return None

    def get_explained_link(self, comic_id):
        return XKCD_EXPLAINED_URL.format(comic_id=comic_id)

    def _load_indexes(self):
        while True:
            # Get metadata
            meta = self._get_meta(self.next_index)
            if not meta:
                return

            # comic_id -> json
            self.json_index[self.next_index] = meta['json_data']

            # image_url_path_part -> comic_id
            parsed = urlparse.urlparse(meta['json_data'].get('img', ''))
            if parsed.path and parsed.path not in self.reverse_image_index:
                self.reverse_image_index[parsed.path] = self.next_index

            # avg_hash -> comic_id
            if meta['hash_avg'] and meta['hash_avg'] not in self.reverse_hash_index:
                self.reverse_hash_index[meta['hash_avg']] = self.next_index

            self.next_index += 1

    def _get_meta(self, comic_id):
        meta = self.datastore.get_xkcd_meta(comic_id)
        if not meta:
            comic_id, json_data, hash_avg, hash_d, hash_p = self._build_xkcd_meta(comic_id)
            if comic_id is not None:
                self.datastore.insert_xkcd_meta(comic_id, json_data, hash_avg, hash_d, hash_p)
                meta = self.datastore.get_xkcd_meta(comic_id)
        return meta

    def _build_xkcd_meta(self, comic_id):
        j = self._get_xkcd_json(comic_id)
        if j:
            hash_avg, hash_d, hash_p = self._get_image_hashes(j.get('img'))
            return comic_id, j, hash_avg, hash_d, hash_p
        return None, None, None, None, None

    def _get_image_hashes(self, url):
        return '', '', ''

    """
    def _get_image_hashes(self, url):
        if not url:
            return '', '', ''
        file_name = '/tmp/' + get_random_file_name()
        try:
            self.myopener.retrieve(url, file_name)
            hash_avg = imagehash.average_hash(Image.open(file_name))
            hash_d = imagehash.dhash(Image.open(file_name))
            hash_p = imagehash.phash(Image.open(file_name))
            return str(hash_avg), str(hash_d), str(hash_p)
        except Exception as e:
            logger.exception('Exception while getting image hashes')
            return '', '', ''
        finally:
            os.remove(file_name)
    """

    def _get_xkcd_json(self, comic_id):
        if int(comic_id) == 404:
            return {'title': '404', 'transcript': '404', 'alt': '404', 'img': '', 'num': 404}

        try:
            response = urllib2.urlopen(XKCD_JSON_API_URL.format(comic_id=comic_id))
            html = response.read()
            return simplejson.loads(html)
        except Exception as e:
            # logger.exception('Exception while getting xkcd json')
            return None

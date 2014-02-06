from collections import defaultdict
import operator
import re
import time
import urllib2
from urlparse import urlparse
from PIL import Image
import imagehash
import os
import uuid
import threading
import hashlib

import simplejson as json

from base import write_line, write_err
from base import PMTriggeredBot, CommentTriggeredBot, SubmissionTriggeredBot, MyOpener
import settings


FULL_EMOTE_REGEX = re.compile('\[[^\[\]\(\)/]*\]\(/[^\[\]\(\)/]*\)')
EMOTE_REGEX = re.compile('/[a-zA-Z0-9_]+')

VALID_ULR_CHARS_REGEX = "[a-zA-Z0-9\-_.~!*'();:@&=+$,/?#[\]]"
XKCD_URL_REGEX = re.compile('(https?://(?:www\.)?(?:imgs\.)?xkcd.com/(?:(?:\d+)|(?:%s+\.[a-zA-Z]+)))' % VALID_ULR_CHARS_REGEX)
IMGUR_URL_REGEX = re.compile('((?:http://)?imgur\.com/\w+)')
XKCD_EXPLAINED_URL = 'http://www.explainxkcd.com/wiki/index.php?title={comic_id}#Explanation'

XKCD_JSON_API_URL = 'http://xkcd.com/{comic_id}/info.0.json'
IMGUR_JSON_API_URL = 'https://api.imgur.com/3/image/{image_id}.json'

MAX_MESSAGE_LENGTH = 10000


class TopEmotesBot(PMTriggeredBot):
    def __init__(self, *args, **kwargs):
        super(TopEmotesBot, self).__init__(*args, **kwargs)

    def _check(self, mail):
        return PMTriggeredBot._check(self, mail)

    def _do(self, mail):
        try:
            comments = mail.author.get_comments(limit=None)
        except Exception as e:
            write_line(' => Exception while getting comments in TopEmotesBot.')
            write_err(e)
            return False

        emotes_dict = defaultdict(int)

        # Parse each comment for emotes
        for comment in comments:
            matches = re.findall(FULL_EMOTE_REGEX, comment.body)
            if matches:
                for match in matches:
                    emote = re.search(EMOTE_REGEX, match)
                    if emote:
                        emotes_dict[emote.group(0).lower()] += 1

        # Remove [](/sp)
        if '/sp' in emotes_dict:
            del emotes_dict['/sp']

        # Remove [](/spoiler)
        if '/spoiler' in emotes_dict:
            del emotes_dict['/spoiler']

        # Sort and reverse
        sorted_emotes = list(reversed(sorted(emotes_dict.iteritems(), key=operator.itemgetter(1))))

        # Build the reply message
        if len(sorted_emotes) == 0:
            reply_msg = "[](/rdcry) You haven't yet used any emotes. You should use them.\n" \
                        '[](/sp)\n' \
                        '\n---\n' \
                        '[](/scootacheer) ^Report ^all ^problems ^to ^/u/LunarMist2 ^| ^[Source](https://github.com/JeremySimpson/redditbot)'
        else:
            reply_msg_header = 'Your emote counts:\n\n' \
                               'Emote | Count\n' \
                               ':--:|:--:\n'

            reply_msg_sig = '\n---\n' \
                            '[](/scootacheer) ^Report ^all ^problems ^to ^/u/LunarMist2 ^| ^[Source](https://github.com/JeremySimpson/redditbot)'

            table_content = ''
            for emote, count in sorted_emotes:
                tr = '{emote}|{count}\n'.format(emote=emote, count=count)
                if len(reply_msg_header) + len(table_content) + len(tr) + len(reply_msg_sig) >= MAX_MESSAGE_LENGTH:
                    break
                else:
                    table_content += tr

            reply_msg = reply_msg_header + table_content + reply_msg_sig

        # Reply to the user and mark it as read
        try:
            self.bot.reply(mail.name, reply_msg)
            mail.mark_as_read()
            #write_line(reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(' => Exception while replying in TopEmotesBot.')
            write_err(e)
            return False

        return True


class ImgurFetcher(object):
    def get_image_url(self, image_id):
        j = self._get_json(image_id)
        return j['data']['link'] if j else None

    def _get_json(self, image_id):
        try:
            req = urllib2.Request(IMGUR_JSON_API_URL.format(image_id=image_id))
            req.add_header('Authorization', settings.IMGUR_AUTHORIZATION)
            response = urllib2.urlopen(req)
            html = response.read()
            return json.loads(html)
        except:
            return None


def get_random_file_name():
    return str(uuid.uuid4())


def get_image_hash(url):
    file_name = '/tmp/' + get_random_file_name()
    imgur = ImgurFetcher()
    myopener = MyOpener()

    if not url.startswith('http'):
        url = '//' + url
    parsed = urlparse(url)
    imgur_url = imgur.get_image_url(parsed.path[1:])

    try:
        myopener.retrieve(imgur_url, file_name)
        return str(imagehash.dhash(Image.open(file_name)))
    except:
        return None
    finally:
        os.remove(file_name)


class XkcdFetcher(object):
    def __init__(self, bot):
        self.bot = bot
        self.next_index = 1
        self.reverse_image_index = {}
        self.reverse_hash_index = {}
        self.index_json = {}
        self.myopener = MyOpener()
        self.lock = threading.Lock()

    def get_json(self, url):
        if not url.startswith('http'):
            url = '//' + url
        parsed = urlparse(url)
        if not parsed:
            return None

        if re.match('^(www\.)?imgs.xkcd.com$', parsed.netloc):
            if parsed.path not in self.reverse_image_index:
                self._load_reverse()
            comic_id = self.reverse_image_index.get(parsed.path)
            return self.index_json.get(comic_id) if comic_id else None

        if re.match('^(www\.)?xkcd.com$', parsed.netloc) and re.match('^/\d+/?$', parsed.path):
            m = re.search('^/(\d+)/?$', parsed.path)
            comic_id = int(m.group(1))
            if comic_id not in self.index_json:
                self._load_reverse()
            return self.index_json.get(comic_id) if comic_id else None

        if re.match('^imgur\.com$', parsed.netloc):
            hash = self.bot.imgur_lookup.get(url)
            if hash:
                if hash not in self.reverse_hash_index:
                    self._load_reverse()
                comic_id = self.reverse_hash_index.get(hash)
                j = self.index_json.get(comic_id) if comic_id else None
                if j:
                    j['from_external'] = True
                return j

        return None

    def get_explained_link(self, comic_id):
        return XKCD_EXPLAINED_URL.format(comic_id=comic_id)

    def _load_reverse(self):
        self.lock.acquire()
        data_store = self.bot._get_new_data_store_connection()
        try:
            while True:
                meta = self._get_meta(data_store, self.next_index)
                if not meta:
                    self._insert_meta(data_store, self.next_index)
                    meta = self._get_meta(data_store, self.next_index)
                if not meta:
                    return

                if meta[1]:  # json
                    self.index_json[self.next_index] = json.loads(meta[1])
                if meta[3] and meta[3] not in self.reverse_hash_index:  # hash_avg
                    self.reverse_hash_index[meta[3]] = self.next_index
                if meta[1]:  # json
                    parsed = urlparse(self.index_json[self.next_index].get('img', ''))
                    if parsed and parsed.path and parsed.path not in self.reverse_image_index:
                        self.reverse_image_index[parsed.path] = self.next_index

                self.next_index += 1
        finally:
            self.lock.release()
            data_store.close()

    def _get_meta(self, data_store, comic_id):
        return data_store.get_xkcd_meta(comic_id)

    def _insert_meta(self, data_store, comic_id):
        j = self._get_xkcd_json(comic_id)
        hash_avg = ''
        hash_d = ''
        hash_p = ''
        if not j:
            return
        if j.get('img'):
            file_name = '/tmp/' + get_random_file_name()
            try:
                self.myopener.retrieve(j.get('img'), file_name)
                hash_avg = imagehash.average_hash(Image.open(file_name))
                hash_d = imagehash.dhash(Image.open(file_name))
                hash_p = imagehash.phash(Image.open(file_name))
            except:
                pass
            finally:
                os.remove(file_name)
        data_store.insert_xkcd_meta(comic_id, json.dumps(j), str(hash_avg), str(hash_d), str(hash_p))

    def _get_xkcd_json(self, comic_id):
        if int(comic_id) == 404:
            return {'title': '404', 'transcript': '404', 'alt': '404'}

        try:
            response = urllib2.urlopen(XKCD_JSON_API_URL.format(comic_id=comic_id))
            html = response.read()
            return json.loads(html)
        except:
            return None


class SubmissionXkcdBot(SubmissionTriggeredBot):
    def __init__(self, *args, **kwargs):
        super(SubmissionXkcdBot, self).__init__(*args, **kwargs)
        self.xkcd = XkcdFetcher(self)

    def _check(self, submission):
        if submission.is_self or submission.subreddit.display_name.lower().find('xkcd') != -1:
            return False

        if submission.url.lower().find('xkcd.com') == -1:
            return False

        return SubmissionTriggeredBot._check(self, submission)

    def _do(self, submission):
        data = self.xkcd.get_json(submission.url)
        if not data:
            write_line(' => Data could not be fetched for {url}'.format(url=submission.url))
            return True

        if data.get('num'):
            self.data_store.increment_xkcd_count(data.get('num'))
            timestamp = int(time.time())
            author = submission.author.name if submission.author else '[deleted]'
            sub = submission.subreddit.display_name
            link = submission.permalink
            self.data_store.insert_xkcd_event(data.get('num'), timestamp, sub, author, link, False)

        if data.get('transcript', '') == '':
            write_line(' => Skipping...transcript is blank.')
            return True

        reply_msg_body = ''
        reply_msg_sig = '---\n' \
                        '^[Questions/Problems](http://www.reddit.com/r/xkcd_transcriber/) ^| ^[Website](http://xkcdref.info/statistics/)'

        if data.get('img'):
            reply_msg_body += u'[Image]({image})\n\n'.format(image=data.get('img').replace('(', '\\(').replace(')', '\\)'))
        if submission.url.find('imgs') != -1:
            reply_msg_body += u'[Original Source](http://xkcd.com/{num}/)\n\n'.format(num=data.get('num', ''))
        if data.get('title'):
            reply_msg_body += u'**Title:** {title}\n\n'.format(title=data.get('title', '').replace('\n', '\n\n'))
        if data.get('transcript'):
            reply_msg_body += u'**Transcript:** {transcript}\n\n'.format(transcript=re.sub('\n{{.+}}', '', data.get('transcript', '')).replace('\n', '\n\n'))
        if data.get('alt'):
            reply_msg_body += u'**Title-text:** {alt}\n\n'.format(alt=data.get('alt', '').replace('\n', '\n\n'))

        explained = self.xkcd.get_explained_link(data.get('num'))
        if explained:
            reply_msg_body += u'[Comic Explanation]({link})\n\n'.format(link=explained)
        stats = self.data_store.get_stats(data.get('num'))
        if stats:
            reply_msg_body += u'**Stats:** This comic has been referenced {0} time(s), representing {1:.2f}% of referenced xkcds.\n\n'.format(stats[0], stats[1])

        reply_msg = reply_msg_body + reply_msg_sig

        # Reply to the user and mark it as read
        try:
            self.bot.reply(submission.name, reply_msg.encode('utf-8'))
            #write_line(reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(' => Exception while replying in SubmissionXkcdBot.')
            write_err(e)
            return False

        return True


class CommentXkcdBot(CommentTriggeredBot):
    def __init__(self, *args, **kwargs):
        super(CommentXkcdBot, self).__init__(*args, **kwargs)
        self.xkcd = XkcdFetcher(self)
        self.imgur_lookup = {}
        self.tmp_flags = {}

    def _check(self, comment):
        if comment.subreddit.display_name.lower().find('xkcd') != -1:
            return False

        #if comment.body.lower().find('imgur.com') == -1:
        #if comment.body.lower().find('xkcd.com') == -1 and comment.body.lower().find('imgur.com') == -1:
        if comment.body.lower().find('xkcd.com') == -1:
            return False

        return CommentTriggeredBot._check(self, comment)

    def _do(self, comment):
        # Get all urls
        urls = self._get_urls(comment.body)
        if not urls:
            write_line(comment.body)
            write_line(' => Skipping..was a false positive (A).')
            return True

        if self.use_threaded:
            delay_processing = False
            tmp_id = hashlib.md5(str(urls)).hexdigest()
            self.tmp_flags[tmp_id] = [len(urls), 0]  # total, current count

            for url in urls:
                if 'imgur.com' in url:
                    def tmp_done(result):
                        self.imgur_lookup[url] = result

                        if tmp_id in self.tmp_flags:
                            self.tmp_flags[tmp_id][1] += 1
                            if self.tmp_flags[tmp_id][1] >= self.tmp_flags[tmp_id][0]:
                                self._process_urls(comment, urls)
                                del self.tmp_flags[tmp_id]

                    self.pool.apply_async(get_image_hash, args=(url,), callback=tmp_done)
                    delay_processing = True

            if delay_processing:
                return True
            else:
                del self.tmp_flags[tmp_id]
                return self._process_urls(comment, urls)
        else:
            return self._process_urls(comment, urls)

    def _process_urls(self, comment, urls):
        reply_msg_sig = '---\n' \
                        '^[Questions/Problems](http://www.reddit.com/r/xkcd_transcriber/) ^| ^[Website](http://xkcdref.info/statistics/)'
        reply_msg_body = ''
        comics_parsed = set()

        # Check each URL for an xkcd reference
        for url in urls:
            data = self.xkcd.get_json(url)
            if data and data.get('num') not in comics_parsed:
                if data.get('num'):
                    self.data_store.increment_xkcd_count(data.get('num'))
                    timestamp = int(time.time())
                    author = comment.author.name if comment.author else '[deleted]'
                    sub = comment.subreddit.display_name
                    link = comment.permalink
                    self.data_store.insert_xkcd_event(data.get('num'), timestamp, sub, author, link, data.get('from_external', False))

                if reply_msg_body != '':
                    reply_msg_body += u'----\n'

                if url.find('imgs') != -1 or data.get('from_external') is True:
                    reply_msg_body += u'[Original Source](http://xkcd.com/{num}/)\n\n'.format(num=data.get('num', ''))
                elif data.get('img'):
                    reply_msg_body += u'[Image]({image})\n\n'.format(image=data.get('img').replace('(', '\\(').replace(')', '\\)'))
                if data.get('title'):
                    reply_msg_body += u'**Title:** {title}\n\n'.format(title=data.get('title', '').replace('\n', '\n\n'))
                if data.get('alt'):
                    reply_msg_body += u'**Title-text:** {alt}\n\n'.format(alt=data.get('alt', '').replace('\n', '\n\n'))

                explained = self.xkcd.get_explained_link(data.get('num'))
                if explained:
                    reply_msg_body += u'[Comic Explanation]({link})\n\n'.format(link=explained)
                stats = self.data_store.get_stats(data.get('num'))
                if stats:
                    reply_msg_body += u'**Stats:** This comic has been referenced {0} time(s), representing {1:.2f}% of referenced xkcds.\n\n'.format(stats[0], stats[1])

                comics_parsed.add(data.get('num'))

        # Do not send if there's no body
        if len(reply_msg_body.strip()) == 0:
            #write_line(' => Skipping..was a false positive (B).')
            return True

        reply_msg = reply_msg_body + reply_msg_sig

        # Reply to the user
        return self._attempt_reply(comment, reply_msg)

    def _attempt_reply(self, message, reply_msg):
        # Ensure I can respond to the user
        if message.author and message.author.name.lower() in self.data_store.get_ignores():
            write_line('Skipping message {id}. Reason: Author on ignore list.'.format(id=message.id))
            return True

        # Reply to the user
        try:
            self.bot.reply(message.name, reply_msg.encode('utf-8'))
            #write_line(reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(' => Exception while replying in CommentXkcdBot.')
            write_err(e)
            return False

        return True

    def _get_urls(self, text):
        all = re.findall(XKCD_URL_REGEX, text)
        all2 = re.findall(IMGUR_URL_REGEX, text)
        urls = [t for t in all] + [t for t in all2]
        return urls

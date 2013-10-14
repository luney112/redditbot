from collections import defaultdict
import operator
import random
import re
import sys
import urllib2
from urlparse import urlparse

import simplejson as json

from base import write_line, write_err
from base import PMTriggeredBot, CommentTriggeredBot, SubmissionTriggeredBot


FULL_EMOTE_REGEX = re.compile('\[[^\[\]\(\)/]*\]\(/[^\[\]\(\)/]*\)')
EMOTE_REGEX = re.compile('/[a-zA-Z0-9_]+')

VALID_ULR_CHARS_REGEX = "[a-zA-Z0-9\-_.~!*'();:@&=+$,/?#[\]]"
XKCD_URL_REGEX = re.compile('((https?://)?(www\.)?(imgs\.)?xkcd.com/((\d+)|(%s+\.[a-zA-Z]+)))' % VALID_ULR_CHARS_REGEX)
XKCD_EXPLAINED_URL = 'http://www.explainxkcd.com/wiki/index.php?title={comic_id}#Explanation'

XKCD_EXPLAINED_JSON_API_URL = 'http://www.explainxkcd.com/wiki/api.php?redirects=true&format=json&action=query&prop=revisions&rvprop=content&rvsection={section}&titles={comic_id}'
XKCD_JSON_API_URL = 'http://xkcd.com/{comic_id}/info.0.json'

BEST_SHIP_KEYS = [
    'best ship',
    'fav ship',
    'favourite ship',
    'is otp',
    'my otp',
]

BEST_SHIP_IMAGES = [
    'http://fc00.deviantart.net/fs71/i/2013/233/b/5/for_your_eyes_only___twidash_wallpaper_by_avareq-d6j41u3.png',
    'http://fc04.deviantart.net/fs70/f/2013/116/f/d/sunset_skies_by_otakuap-d623vd9.jpg',
    'http://fc07.deviantart.net/fs70/i/2012/194/d/8/reading_rainbow_by_dogaxiii-d574umv.jpg',
    'http://fc00.deviantart.net/fs70/i/2011/248/5/1/essential_twilight_and_dashie_by_the_gneech-d490lfp.jpg',
    'http://fc03.deviantart.net/fs71/f/2011/337/f/6/twidash_moment_by_smittyg-d4i19tu.png',
    'http://th05.deviantart.net/fs71/PRE/f/2013/078/c/e/twidash_by_murries-d5ym2cg.png',
    'http://fc03.deviantart.net/fs70/i/2013/008/8/7/twidash_by_gamesadict-d5qlnmt.png',
    'http://th09.deviantart.net/fs70/PRE/f/2013/034/2/1/winghugs_by_nyuuchandiannepie-d5tp1ri.jpg',
    'http://th07.deviantart.net/fs70/PRE/i/2012/167/f/3/save_your_sky_for_me_by_nyuuchandiannepie-d53nzd8.png',
    'http://th03.deviantart.net/fs70/PRE/i/2012/123/f/3/twidash_in_the_rain_by_nyuuchandiannepie-d4ydmwj.png',
    'http://th08.deviantart.net/fs71/PRE/i/2012/116/2/a/afterthewedding_by_nyuuchandiannepie-d4xf0aq.png',
    'http://th09.deviantart.net/fs71/PRE/i/2011/365/6/d/keeping_warm_by_nyuuchandiannepie-d4ktqpl.png',
    'http://th02.deviantart.net/fs70/PRE/i/2011/363/a/9/dance_till_were_high_by_nyuuchandiannepie-d4klr05.png',
    'http://th03.deviantart.net/fs70/PRE/i/2011/352/4/8/hearthswarmingtwidash_by_nyuuchandiannepie-d4jg584.png',
    'http://th02.deviantart.net/fs70/PRE/i/2011/341/f/c/lunafied_twidash_by_nyuuchandiannepie-d4if24y.png',
    'http://th06.deviantart.net/fs71/PRE/i/2011/339/0/7/shall_we_dance_by_nyuuchandiannepie-d4i8k0j.png',
    'http://th00.deviantart.net/fs71/PRE/i/2011/334/9/6/twilight_is_best_pet_by_nyuuchandiannepie-d4hqgcy.jpg',
    'http://th09.deviantart.net/fs70/PRE/i/2012/132/7/4/sick_twidash_by_nyuuchandiannepie-d4zhd91.png',
    'http://th02.deviantart.net/fs71/PRE/i/2011/285/d/a/entwined_by_nyuuchandiannepie-d4cm685.jpg',
    'http://th02.deviantart.net/fs70/PRE/i/2011/284/3/1/a_day_out_with_dash_by_nyuuchandiannepie-d4cinri.jpg',
    'http://th06.deviantart.net/fs70/PRE/i/2011/281/6/4/sunddenly__raibow_dash_by_nyuuchandiannepie-d4c5vfx.jpg',
]

PONY_SUBS = 'mylittlepony+mlplounge+ploungeafterdark+cloudchasermotes'
MAX_MESSAGE_LENGTH = 10000


class BestShipBot(CommentTriggeredBot):
    def __init__(self, *args, **kwargs):
        random.seed(None)
        super(BestShipBot, self).__init__(*args, **kwargs)

    def _check(self, comment):
        comment_body = comment.body.lower()
        for key in BEST_SHIP_KEYS:
            if comment_body.find(key) != -1:
                return CommentTriggeredBot._check(self, comment)

        return False

    def _do(self, comment):
        reply_msg = 'I heard you like the [best ship]({image})'.format(image=self._get_random_image())

        # Reply to the comment
        try:
            self.bot.reply(comment.name, reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(' => Exception while replying in BestShipBot.')
            write_err(e)
            return False

        return True

    def _get_random_image(self):
        return BEST_SHIP_IMAGES[random.randint(0, len(BEST_SHIP_IMAGES) - 1)]


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


class XkcdFetcher(object):
    def __init__(self):
        self.next_index = 1
        self.reverse_index = {}

    def get_json(self, url):
        parsed = urlparse(url)
        if not parsed:
            return None

        if re.match('^(www\.)?imgs.xkcd.com$', parsed.netloc):
            self._get_new_reverse_entries()
            m = self.reverse_index.get(parsed.path, '')
            return self._get_xkcd_json(m) if m else None

        if re.match('^(www\.)?xkcd.com$', parsed.netloc) and re.match('^/\d+/?$', parsed.path):
            m = re.search('^/(\d+)/?$', parsed.path)
            return self._get_xkcd_json(m.group(1))

        return None

    def get_explanation(self, comic_id):
        try:
            response = urllib2.urlopen(XKCD_EXPLAINED_JSON_API_URL.format(section=1, comic_id=comic_id))
            html = response.read()
            j = json.loads(html)
            return j['query']['pages'].values()[0]['revisions'][0]['*']
        except Exception as e:
            return None

    def get_explained_link(self, comic_id):
        return XKCD_EXPLAINED_URL.format(comic_id=comic_id)

    def _get_xkcd_json(self, comic_id):
        if int(comic_id) == 404:
            return {'title': '404', 'transcript': '404', 'alt': '404'}

        try:
            response = urllib2.urlopen(XKCD_JSON_API_URL.format(comic_id=comic_id))
            html = response.read()
            return json.loads(html)
        except Exception as e:
            return None

    def _get_new_reverse_entries(self):
        while True:
            json = self._get_xkcd_json(self.next_index)
            if not json:
                return

            parsed = urlparse(json.get('img', ''))
            if parsed and parsed.path:
                self.reverse_index[parsed.path] = self.next_index

            self.next_index += 1


class SubmissionXkcdBot(SubmissionTriggeredBot):
    def __init__(self, *args, **kwargs):
        self.xkcd = XkcdFetcher()
        super(SubmissionXkcdBot, self).__init__(*args, **kwargs)

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

        if data.get('transcript', '') == '':
            write_line(' => Skipping...transcript is blank.')
            return True

        reply_msg_body = ''
        reply_msg_sig = ''

        if data.get('img'):
            reply_msg_body += '[Image]({image})\n\n'.format(image=data.get('img'))
        if submission.url.find('imgs') != -1:
            reply_msg_body += '[Original Source](http://xkcd.com/{num}/)\n\n'.format(num=data.get('num', ''))
        if data.get('title'):
            reply_msg_body += '**Title:** {title}\n\n'.format(title=data.get('title', '').replace('\n', '\n\n'))
        if data.get('transcript'):
            reply_msg_body += '**Transcript:** {transcript}\n\n'.format(transcript=re.sub('\n{{.+}}', '', data.get('transcript', '')).replace('\n', '\n\n'))
        if data.get('alt'):
            reply_msg_body += '**Alt-text:** {alt}\n\n'.format(alt=data.get('alt', '').replace('\n', '\n\n'))

        explained = self.xkcd.get_explained_link(data.get('num'))
        if explained:
            reply_msg_body += '[Comic Explanation]({link})\n\n'.format(link=explained)

        reply_msg = reply_msg_body.strip() + reply_msg_sig

        # Reply to the user and mark it as read
        try:
            self.bot.reply(submission.name, reply_msg)
            #write_line(reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(' => Exception while replying in SubmissionXkcdBot.')
            write_err(e)
            return False

        return True


class CommentXkcdBot(CommentTriggeredBot):
    def __init__(self, *args, **kwargs):
        self.xkcd = XkcdFetcher()
        super(CommentXkcdBot, self).__init__(*args, **kwargs)

    def _check(self, comment):
        if comment.subreddit.display_name.lower().find('xkcd') != -1:
            return False

        if comment.body.lower().find('xkcd.com') == -1:
            return False

        return CommentTriggeredBot._check(self, comment)

    def _do(self, comment):
        # Get all urls
        urls = self._get_urls(comment.body)
        if not urls:
            write_line(' => Skipping..was a false positive.')
            return True

        reply_msg_sig = ''
        reply_msg_body = ''
        comics_parsed = set()

        # Check each URL for an xkcd reference
        for url in urls:
            data = self.xkcd.get_json(url)
            if data and data.get('num') not in comics_parsed:
                if reply_msg_body != '':
                    reply_msg_body += '----\n'

                if url.find('imgs') != -1:
                    reply_msg_body += '[Original Source](http://xkcd.com/{num}/)\n\n'.format(num=data.get('num', ''))
                elif data.get('img'):
                    reply_msg_body += '[Image]({image})\n\n'.format(image=data.get('img'))
                if data.get('title'):
                    reply_msg_body += '**Title:** {title}\n\n'.format(title=data.get('title', '').replace('\n', '\n\n'))
                if data.get('alt'):
                    reply_msg_body += '**Alt-text:** {alt}\n\n'.format(alt=data.get('alt', '').replace('\n', '\n\n'))

                explained = self.xkcd.get_explained_link(data.get('num'))
                if explained:
                    reply_msg_body += '[Comic Explanation]({link})\n\n'.format(link=explained)

                comics_parsed.add(data.get('num'))

        # Do not send if there's no body
        if len(reply_msg_body.strip()) == 0:
            write_line(' => Skipping..was a false positive.')
            return True

        reply_msg = reply_msg_body.strip() + reply_msg_sig

        # Reply to the user
        try:
            self.bot.reply(comment.name, reply_msg)
            #write_line(reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(' => Exception while replying in CommentXkcdBot.')
            write_err(e)
            return False

        return True

    def _get_urls(self, text):
        all = re.findall(XKCD_URL_REGEX, text)
        return [t[0] for t in all]


if __name__ == '__main__':
    counts_emotes_handler = TopEmotesBot(user_agent='Emote counter by ----',
                                         username='----',
                                         password='----',
                                         delay=30,
                                         fetch_limit=None,
                                         cache_size=None)

    best_ship_handler = BestShipBot(user_agent='Best Ship Bot by ----',
                                    username='----',
                                    password='----',
                                    subreddit=PONY_SUBS,
                                    delay=30,
                                    fetch_limit=60,
                                    cache_size=120)

    xkcd_transcriber_handler_s = SubmissionXkcdBot(user_agent='xkcd transcriber Bot by ----',
                                                   username='----',
                                                   password='----',
                                                   subreddit='all',
                                                   delay=30,
                                                   fetch_limit=200,
                                                   cache_size=400)

    xkcd_transcriber_handler_c = CommentXkcdBot(user_agent='xkcd transcriber Bot by ----',
                                                username='----',
                                                password='----',
                                                subreddit='all',
                                                delay=30,
                                                fetch_limit=None,
                                                cache_size=2000)

    bots = {
        'top_emotes': counts_emotes_handler,
        'best_ship': best_ship_handler,
        'xkcd_transcriber_s': xkcd_transcriber_handler_s,
        'xkcd_transcriber_c': xkcd_transcriber_handler_c,
    }

    if len(sys.argv) != 2 or sys.argv[1] not in bots:
        print 'Usage:', sys.argv[0], 'botname'
        print 'Bot names:'
        for bot_name in sorted(bots.keys()):
            print '    ', bot_name
    else:
        bot = bots[sys.argv[1]]
        bot.run()

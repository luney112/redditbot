from collections import defaultdict
import re
import operator
import sys

from base import write_line, BaseHandler, PMTriggeredBot, CommentTriggeredBot

FULL_EMOTE_REGEX = re.compile('\[[^\[\]\(\)/]*\]\(/[^\[\]\(\)/]*\)')
EMOTE_REGEX = re.compile('/[a-zA-Z0-9]+')

BEST_SHIP_KEYS = [
    'best ship',
    'fav ship',
    'favourite ship',
    'is otp',
    'my otp',
    'twidash',
]
BEST_SHIP_IMAGE = 'http://fc00.deviantart.net/fs71/i/2013/233/b/5/for_your_eyes_only___twidash_wallpaper_by_avareq-d6j41u3.png'
PONY_SUBS = 'mylittlepony+mlplounge+ploungeafterdark'
MAX_MESSAGE_LENGTH = 10000


class BestShipHandler(BaseHandler):
    def check(self, comment):
        key_found = False
        comment.body = comment.body.lower()
        for key in BEST_SHIP_KEYS:
            if comment.body.find(key) != -1:
                key_found = True
                break

        return key_found

    def do(self, comment):
        reply_msg = 'I heard you like the [best ship]({image})'.format(image=BEST_SHIP_IMAGE)

        # Reply to the comment
        try:
            comment.reply(reply_msg)
            write_line('Reply Sent!')
        except Exception as e:
            write_line(e)
            return False

        return True


class TopEmotesHandler(BaseHandler):
    def check(self, mail):
        return True

    def do(self, mail):
        try:
            comments = mail.author.get_comments(limit=None)
        except Exception as e:
            write_line(e)
            return False

        emotes_dict = defaultdict(int)

        # Parse each comment for emotes
        for comment in comments:
            matches = re.findall(FULL_EMOTE_REGEX, comment.body)
            if matches:
                for match in matches:
                    emote = re.search(EMOTE_REGEX, match)
                    if emote:
                        emotes_dict[emote.group(0)] += 1

        # Remove [](/sp)
        if '/sp' in emotes_dict:
            del emotes_dict['/sp']

        # Remove [](/spoiler)
        if '/spoiler' in emotes_dict:
            del emotes_dict['/spoiler']

        # Sort and reverse
        sorted_emotes = reversed(sorted(emotes_dict.iteritems(), key=operator.itemgetter(1)))

        # Build the reply message
        reply_msg_header = 'Your emote counts:\n\n' \
                           'Emote | Count\n' \
                           ':--:|:--:\n'
                    
        reply_msg_sig = '---\n' \
                        '[](/scootacheer) ^Report ^all ^problems ^to ^/u/LunarMist2 ^| ^[Source](https://github.com/JeremySimpson/redditbot)'

        table_content = ''
        for emote, count in sorted_emotes:
            tr = '{emote}|{count}\n'.format(emote=emote, count=count)
            if len(reply_msg_header) + len(table_content) + len(tr) + len(reply_msg_sig) >= MAX_MESSAGE_LENGTH:
                break
            else:
                table_content += tr

        # Reply to the user and mark it as read
        try:
            reply_msg = reply_msg_header + table_content + reply_msg_sig
            mail.reply(reply_msg)
            mail.mark_as_read()
            #write_line(reply_msg)
            write_line(' => Reply Sent!')
        except Exception as e:
            write_line(e)
            return False

        return True


if __name__ == '__main__':

    bots = {
        'top_emotes': PMTriggeredBot('Emote counter by /u/LunarMist2', '--', '--', TopEmotesHandler(), 10),
        'best_ship': CommentTriggeredBot(PONY_SUBS, 15, 'Best Ship Bot by /u/LunarMist2', '--', '--', BestShipHandler(), 20),
    }

    if len(sys.argv) != 2 or sys.argv[1] not in bots:
        print 'Usage:', sys.argv[0], 'botname'
        print 'Bot names:'
        for bot_name in bots.keys():
            print '    ', bot_name
    else:
        bot = bots[sys.argv[1]]
        bot.run()

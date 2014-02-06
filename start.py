import sys

from bot import TopEmotesBot, SubmissionXkcdBot, CommentXkcdBot
import settings

if __name__ == '__main__':
    def counts_emotes_handler():
        return TopEmotesBot(user_agent='Emote counter by %s' % settings.AUTHOR,
                            username='counts_your_emotes',
                            password=settings.REDDIT_ACCOUNTS['counts_your_emotes'],
                            delay=30,
                            fetch_limit=None,
                            cache_size=None)

    def xkcd_transcriber_handler_s():
        return SubmissionXkcdBot(user_agent='xkcd transcriber Bot by %s' % settings.AUTHOR,
                                 username='xkcd_transcriber',
                                 password=settings.REDDIT_ACCOUNTS['xkcd_transcriber'],
                                 subreddit='all',
                                 delay=30,
                                 fetch_limit=200,
                                 cache_size=400)

    def xkcd_transcriber_handler_c():
        return CommentXkcdBot(user_agent='xkcd transcriber Bot by %s' % settings.AUTHOR,
                              username='xkcd_transcriber',
                              password=settings.REDDIT_ACCOUNTS['xkcd_transcriber'],
                              subreddit='all',
                              delay=20,
                              fetch_limit=None,
                              cache_size=2000,
                              thread_limit=0)

    bots = {
        'top_emotes': counts_emotes_handler,
        'xkcd_transcriber_s': xkcd_transcriber_handler_s,
        'xkcd_transcriber_c': xkcd_transcriber_handler_c,
    }

    if len(sys.argv) != 2 or sys.argv[1] not in bots:
        print 'Usage:', sys.argv[0], 'botname'
        print 'Bot names:'
        for bot_name in sorted(bots.keys()):
            print '    ', bot_name
    else:
        bot = bots[sys.argv[1]]()
        bot.run()

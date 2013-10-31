import sys
from bot import TopEmotesBot, BestShipBot, SubmissionXkcdBot, CommentXkcdBot

PONY_SUBS = 'mylittlepony+mlplounge+ploungeafterdark+cloudchasermotes'


if __name__ == '__main__':
    counts_emotes_handler = TopEmotesBot(user_agent='Emote counter by /u/-----',
                                         username='----',
                                         password='----',
                                         delay=30,
                                         fetch_limit=None,
                                         cache_size=None)

    best_ship_handler = BestShipBot(user_agent='Best Ship Bot by /u/----',
                                    username='----',
                                    password='----',
                                    subreddit=PONY_SUBS,
                                    delay=30,
                                    fetch_limit=60,
                                    cache_size=120)

    xkcd_transcriber_handler_s = SubmissionXkcdBot(user_agent='xkcd transcriber Bot by /u/----',
                                                   username='----',
                                                   password='----',
                                                   subreddit='all',
                                                   delay=30,
                                                   fetch_limit=200,
                                                   cache_size=400)

    xkcd_transcriber_handler_c = CommentXkcdBot(user_agent='xkcd transcriber Bot by /u/----',
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

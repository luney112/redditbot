# Must be first for monkey_patch()
from redditbot.base import patch_all
patch_all()

import logging

from redditbot.bots import settings
from redditbot.base.handlers import MultiBotHandler
from bot import SubmissionXkcdBot, CommentXkcdBot, MailXkcdBot, VoteXkcdBot
from datastore import BotDataStore
from xkcdfetcher import XkcdFetcher

logging.basicConfig()


def run():
    datastore = BotDataStore('xkcd_transcriber', settings.XKCD_DB_LOCATION)
    xkcd_fetcher = XkcdFetcher(datastore)

    # If fetch_limit is set to None, it will keep on going back for hugely old submissions
    submission_bot = SubmissionXkcdBot(user_agent='xkcdref bot (submission) by %s' % settings.AUTHOR,
                                       auth=settings.REDDIT_ACCOUNTS['xkcd_transcriber'],
                                       delay=20,
                                       fetch_limit=300,
                                       cache_size=600,
                                       dry_run=settings.DRY_RUN,
                                       subreddit='all',
                                       datastore=datastore,
                                       xkcd_fetcher=xkcd_fetcher)

    comment_bot = CommentXkcdBot(user_agent='xkcdref bot (comment) by %s' % settings.AUTHOR,
                                 auth=settings.REDDIT_ACCOUNTS['xkcd_transcriber'],
                                 delay=15,
                                 fetch_limit=None,
                                 cache_size=2000,
                                 dry_run=settings.DRY_RUN,
                                 subreddit='all',
                                 datastore=datastore,
                                 xkcd_fetcher=xkcd_fetcher)

    mail_bot = MailXkcdBot(user_agent='xkcdref bot (message) by %s' % settings.AUTHOR,
                           auth=settings.REDDIT_ACCOUNTS['xkcd_transcriber'],
                           delay=60,
                           fetch_limit=None,
                           cache_size=0,
                           dry_run=settings.DRY_RUN,
                           datastore=datastore,
                           xkcd_fetcher=xkcd_fetcher)

    vote_bot = VoteXkcdBot(user_agent='xkcdref bot (vote) by %s' % settings.AUTHOR,
                           auth=settings.REDDIT_ACCOUNTS['xkcd_transcriber'],
                           delay=300,
                           fetch_limit=None,
                           cache_size=0,
                           dry_run=settings.DRY_RUN,
                           monitored_user='xkcd_transcriber',
                           score_threshold_min=-1)

    # Run all bots
    MultiBotHandler([
        submission_bot,
        comment_bot,
        mail_bot,
        vote_bot
    ]).run()


if __name__ == '__main__':
    run()

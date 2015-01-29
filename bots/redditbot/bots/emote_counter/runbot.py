# Must be first for monkey_patch()
from redditbot.base import patch_all
patch_all()

import logging

from bot import TopEmotesBot
import redditbot.bots.settings as settings

logging.basicConfig(level=logging.INFO)


def run():
    TopEmotesBot(user_agent='Emote counter by %s' % settings.AUTHOR,
                 auth=settings.REDDIT_ACCOUNTS['counts_your_emotes'],
                 delay=60,
                 fetch_limit=None,
                 cache_size=100).run()


if __name__ == '__main__':
    run()

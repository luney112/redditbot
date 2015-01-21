redditbot
=========

This is a reddit bot framework (v2!)

Built-in Templates:
 - Message-triggered bots (PMs, comment replies, post replies, username mentions)
 - Comment-triggered bots
 - Submission-triggered bots
 - Vote-triggered bots

Included working bots:
 - Emote counter (triggered through PMs)
 - XKCD transcriber (trigged via submission and comments, monitors messages to add to ignore list, vote monitoring)

Requires:
 python 2.7, praw, simplejson, snudown, a bunch of other stuff (see requirements.txt)


---

How-to:

1. Subclass UserCommentsVoteTriggeredBot, MailTriggeredBot, SubredditCommentTriggeredBot, SubredditSubmissionTriggeredBot or BotHandler if you need a new type.
 
2. Implement the \_check() and \_do() functions at a minimum. If you are subclassing a template, be sure to call the super() function for each. If not, implement \_get_content() as well.

3. In v1, the built-in bot templates auto checked to ensure it doesn't reply twice. This functionality has been moved into the `utils` module, and needs to be called yourself.

4. `MultiBotHandler` can be used to run multiple bots at the same time in a single python process.

5. It is important that

```
# Must be first for monkey_patch()
from redditbot.base import patch_all
patch_all()
```

are the first lines that execute when the python process is started. These lines ensure that gevent's monkey patches are made correctly.

---

Notes:

1. The example bots can be run with `python runbot.py`

2. Accounts and settings are configured in settings.py

3. local_settings.py can be used to configure dev settings and have git ignore it.

4. Oauth2 support is included (script type apps only).

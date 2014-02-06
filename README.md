redditbot
=========

This is a reddit bot framework.

Supports:
 - Comment-triggered bots
 - PM-triggered bots
 - Submission-triggered bots

Included bots:
 - Emote counter (triggered through PMs)
 - XKCD transcriber (trigged via submission and comments, monitors PMs to add to ignore list)

Requires:
 python 2.7, praw, simplejson, ImageHash (0.3)


----

Notes:
 - Uses praw to access reddit's data.
 - The xkcd bot also supports references of images that were uploaded to imgur. It compares image hashes to find possible references.

---

How-to:

1. Subclass PMTriggeredBot, CommentTriggeredBot, SubmissionTriggeredBot or Bot if you need a new type.
 
2. Be sure to implement the \_check() and \_do() functions at a minimum. If you are subclassing PMTriggeredBot, CommentTriggeredBot or SubmissionTriggeredBot it is IMPORTANT that you call super(...)._check(), or else the bot may double-post or pick up its own replies.

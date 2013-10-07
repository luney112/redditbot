from collections import deque
import sys
from time import sleep

import praw


def write_line(out_str):
    sys.stdout.write(str(out_str))
    sys.stdout.write('\n')
    sys.stdout.flush()


class RedditAPI(object):
    def __init__(self, user_agent, username=None, password=None):
        self.r = praw.Reddit(user_agent)
        self.username = username
        self.password = password

    def login(self):
        try:
            if self.username and self.password and not self.r.is_logged_in():
                self.r.login(self.username, self.password)
        except Exception as e:
            write_line(e)

    def get_unread(self):
        try:
            return self.r.get_unread(limit=None)
        except Exception as e:
            write_line(e)

        return None

    def get_comments(self, subreddit, limit):
        try:
            return self.r.get_comments(subreddit, limit=limit)
        except Exception as e:
            write_line(e)

        return None

    def get_new_submissions(self, subreddit, limit):
        try:
            return self.r.get_subreddit(subreddit).get_new(limit=limit)
        except Exception as e:
            write_line(e)

        return None


class Bot(object):
    def __init__(self, user_agent, username, password, handler, delay):
        self.cache = deque(maxlen=400)
        self.retry = deque(maxlen=100)
        self.bot = RedditAPI(user_agent, username, password)
        self.handler = handler
        self.delay = delay

    def check(self):
        content = self._get_content()
        misses = 0
        hits = 0

        # Process all content
        if content:
            for obj in content:
                # Do not process already-processed content
                if obj.id in self.cache:
                    hits += 1
                else:
                    self.cache.append(obj.id)
                    misses += 1

                    if self.handler.check(obj) and self._extra_check(obj):
                        write_line('Found valid object ' + str(obj.id) + ' from ' + obj.author.name)
                        if not self.handler.do(obj):
                            write_line('Failed to process object ' + str(obj.id) + '. Adding to retry list.')
                            self.retry.append(obj)

            #write_line('Cache hits ' + str(hits) + ', misses ' + str(misses))

        # Retry some in the retry queue
        while len(self.retry) > 0:
            obj = self.retry.popleft()
            if self.handler.check(obj) and self._extra_check(obj):
                if not self.handler.do(obj):
                    write_line('Retried object: ' + str(obj.id) + '. Failed!')
                    self.retry.append(obj)
                    break
                write_line('Retried object: ' + str(obj.id) + '. Success!')
        if len(self.retry) > 0:
            write_line('Retry queue size: ' + str(len(self.retry)))

    def _get_content(self):
        raise NotImplementedError()

    def _extra_check(self, obj):
        return True

    def run(self):
        self.bot.login()
        while True:
            try:
                self.check()
            except Exception as e:
                write_line(e)
            sleep(self.delay)


class PMTriggeredBot(Bot):
    def __init__(self, *args, **kwargs):
        super(PMTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.bot.get_unread()

    def _extra_check(self, message):
        # Ensure it was a PM
        if message.was_comment:
            write_line('Skipping comment with text ' + message.body.split('\n')[0] + '...Reason: not a PM')
            return False

        # Ensure I have not already replied
        if message.first_message is not None:
            write_line('Skipping comment with text ' + message.body.split('\n')[0] + '...Reason: not the first message in thread')
            return False

        return True


class CommentTriggeredBot(Bot):
    def __init__(self, subreddit, fetch_limit=200, *args, **kwargs):
        self.subreddit = subreddit
        self.fetch_limit = fetch_limit
        super(CommentTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.bot.get_comments(self.subreddit, limit=self.fetch_limit)

    def _extra_check(self, comment):
        # Ignore my own comments
        if comment.author.name == self.bot.username:
            write_line('Skipping comment with text ' + comment.body.split('\n')[0] + '...Reason: own comment')
            return False

        # Ensure I have not already replied
        replies = comment.replies
        for reply in replies:
            if reply.author.name == self.bot.username:
                write_line('Skipping comment with text ' + comment.body.split('\n')[0] + '...Reason: already replied')
                return False

        return True


class SubmissionTriggeredBot(Bot):
    def __init__(self, subreddit, fetch_limit=200, *args, **kwargs):
        self.subreddit = subreddit
        self.fetch_limit = fetch_limit
        super(SubmissionTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.bot.get_new_submissions(self.subreddit, limit=self.fetch_limit)

    def _extra_check(self, submission):
        # Ensure I have not already replied
        submission.replace_more_comments(limit=None)
        comments = submission.comments
        for comment in comments:
            if comment.author.name == self.bot.username:
                write_line('Skipping comment with text ' + comment.body.split('\n')[0] + '...Reason: already replied')
                return False

        return True


class BaseHandler(object):
    def check(self, o):
        raise NotImplementedError()

    def do(self, o):
        raise NotImplementedError()

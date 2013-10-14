from collections import deque, OrderedDict
import sys
from time import sleep
import traceback

import praw


def write_line(out_str):
    sys.stdout.write(str(out_str))
    sys.stdout.write('\n')
    sys.stdout.flush()


def write_err(out_str):
    write_line(out_str)
    write_line(traceback.format_exc())


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
            write_err(e)

    def get_unread(self):
        self.login()
        try:
            return self.r.get_unread(limit=None)
        except Exception as e:
            write_err(e)

        return None

    def get_comments(self, subreddit, limit):
        try:
            return self.r.get_comments(subreddit, limit=limit)
        except Exception as e:
            write_err(e)

        return None

    def get_new_submissions(self, subreddit, limit):
        try:
            return self.r.get_subreddit(subreddit).get_new(limit=limit)
        except Exception as e:
            write_err(e)

        return None

    def reply(self, thing_id, text):
        self.login()
        mine = self.get_refreshed(thing_id)
        try:
            if isinstance(mine, praw.objects.Submission):
                mine.add_comment(text)
            else:
                mine.reply(text)
        except Exception as e:
            write_err(e)

    def get_refreshed(self, thing_id):
        try:
            return self.r.get_info(thing_id=thing_id)
        except Exception as e:
            write_err(e)

        return None


class LRUCache(OrderedDict):
    def __init__(self, *args, **kwargs):
        self.size_limit = kwargs.pop('size', None)
        self.size_limit = self.size_limit if self.size_limit > 0 else None
        OrderedDict.__init__(self, *args, **kwargs)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class Bot(object):
    def __init__(self, user_agent, username, password, delay, fetch_limit, cache_size=None, retry_limit=10):
        self.bot = RedditAPI(user_agent, username, password)
        self.delay = delay
        self.fetch_limit = fetch_limit
        self.use_cache = cache_size > 0
        self.cache = LRUCache(size=cache_size)
        self.retry_queue = deque(maxlen=100)
        self.retry_limit = retry_limit

    def main(self):
        content = self._get_content()
        if not content:
            write_line('Bad content object: skipping...')
            return

        hits = 0
        misses = 0

        # Process all content
        for obj in content:
            # Check if it's in the cache
            if self.use_cache:
                if obj.id in self.cache:
                    hits += 1
                    continue
                misses += 1
                self.cache[obj.id] = obj.id

            # Process the object
            if self._check(obj):
                write_line('Found valid object: {id} by {name}.'.format(id=obj.id, name=obj.author.name if obj.author else '[deleted]'))
                if not self._do(obj):
                    write_line('Failed to process object {id}. Added to retry queue.'.format(id=obj.id))
                    self.retry_queue.append((obj, 0))

        #if self.use_cache:
        #    write_line('Cache hits: {hits}, misses: {misses}'.format(hits=hits, misses=misses))

        # Retry some in the retry queue
        self._rety_some()
        if len(self.retry_queue) > 0:
            write_line('Retry queue size: {size}'.format(size=len(self.retry_queue)))

    def _rety_some(self):
        while len(self.retry_queue) > 0:
            # Process each object
            obj, retry_count = self.retry_queue.popleft()
            fresh = self.bot.get_refreshed(obj.name)
            if self._check(fresh):
                if not self._do(fresh):
                    retry_count += 1
                    write_line('Retried object: {id}. Status: Failed. Count: {count}.'.format(id=fresh.id, count=retry_count))
                    if retry_count >= self.retry_limit:
                        write_line('Object {id} failed too many time - removing from queue'.format(id=fresh.id))
                    else:
                        self.retry_queue.append((fresh, retry_count))
                    return
                write_line('Retried object: {id}. Status: Success!'.format(id=fresh.id))
            else:
                write_line('Object {id} in retry queue no long valid...skipping'.format(id=fresh.id))

    def _get_content(self):
        raise NotImplementedError()

    def _check(self):
        raise NotImplementedError()

    def _do(self):
        raise NotImplementedError()

    def run(self):
        write_line('Bot started!')

        while True:
            try:
                self.main()
            except Exception as e:
                write_err(e)
            sleep(self.delay)

        write_line('Bot finished! Exiting gracefully.')


class PMTriggeredBot(Bot):
    def __init__(self, *args, **kwargs):
        super(PMTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.bot.get_unread()

    def _check(self, message):
        # Ensure it was a PM
        if message.was_comment:
            write_line('Skipping message {id}. Reason: Not a PM.'.format(id=message.id))
            message.mark_as_read()
            return False

        # Ensure I have not already replied
        if message.first_message is not None:
            write_line('Skipping message {id}. Reason: Not the first message in the thread.'.format(id=message.id))
            message.mark_as_read()
            return False

        return True


class CommentTriggeredBot(Bot):
    def __init__(self, *args, **kwargs):
        self.subreddit = kwargs.pop('subreddit', None)
        super(CommentTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.bot.get_comments(self.subreddit, limit=self.fetch_limit)

    def _check(self, comment):
        # Ignore my own comments
        if comment.author and comment.author.name == self.bot.username:
            write_line('Skipping comment {id}. Reason: Own comment.'.format(id=comment.id))
            return False

        # Ensure I have not already replied
        replies = comment.replies
        if replies:
            for reply in replies:
                if reply.author and reply.author.name == self.bot.username:
                    write_line('Skipping comment {id}. Reason: Already replied.'.format(id=comment.id))
                    return False

        return True


class SubmissionTriggeredBot(Bot):
    def __init__(self, *args, **kwargs):
        self.subreddit = kwargs.pop('subreddit', None)
        super(SubmissionTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.bot.get_new_submissions(self.subreddit, limit=self.fetch_limit)

    def _check(self, submission):
        # Ensure I have not already replied
        submission.replace_more_comments(limit=None)
        comments = submission.comments
        if comments:
            for comment in comments:
                if comment.author and comment.author.name == self.bot.username:
                    write_line('Skipping submission {id}. Reason: Already replied.'.format(id=submission.id))
                    return False

        return True

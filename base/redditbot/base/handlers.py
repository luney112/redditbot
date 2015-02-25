import time
import logging

import gevent
import praw
import pylru
import requests
import requests.auth

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OAUTH_ACCESS_TOKEN_URL = 'https://www.reddit.com/api/v1/access_token'
OAUTH_SCOPES = {'edit', 'identity', 'modconfig', 'modflair', 'modlog', 'modposts',
                'mysubreddits', 'privatemessages', 'read', 'submit', 'subscribe', 'vote'}


class MultiBotHandler(object):
    def __init__(self, handlers):
        self.handlers = handlers

    def run(self):
        greenlets = []
        for handler in self.handlers:
            greenlets.append(gevent.spawn(handler.run))
        gevent.joinall(greenlets)


class BotHandler(object):
    def __init__(self, user_agent, auth, delay, fetch_limit, cache_size=0, dry_run=False):
        self.user_agent = user_agent
        self.auth = auth
        self.delay = delay
        self.fetch_limit = fetch_limit
        self.cache_size = cache_size
        self.dry_run = dry_run
        self.cache = pylru.lrucache(self.cache_size) if self.cache_size > 0 else None
        self.api_request_delay = 1.0 if self.__is_oauth() else 2.0
        self.r = praw.Reddit(self.user_agent, cache_timeout=0, api_request_delay=self.api_request_delay)
        self.expires = -1
        self.__auth()

    def _get_content(self):
        raise NotImplementedError()

    def _check(self, obj):
        raise NotImplementedError()

    def _do(self, obj):
        raise NotImplementedError()

    def __is_oauth(self):
        return 'client_id' in self.auth and 'secret' in self.auth

    def __update_access_credentials(self):
        # Fetch access token
        client_auth = requests.auth.HTTPBasicAuth(self.auth['client_id'], self.auth['secret'])
        response = requests.post(OAUTH_ACCESS_TOKEN_URL, auth=client_auth, data={
            'grant_type': 'password',
            'username': self.auth['username'],
            'password': self.auth['password']
        }, headers={
            'User-Agent': self.user_agent
        })

        # Check response
        if response.ok:
            response = response.json()
        else:
            logger.error('Could not retrieve access creds: Status {status}'.format(status=response.status_code))
            return

        # Update
        if 'error' in response:
            logger.error('Could not retrieve access creds: Json error: {status}'.format(status=response['error']))
        else:
            self.r.set_access_credentials(scope=OAUTH_SCOPES, access_token=response['access_token'])
            self.expires = time.time() + int(response['expires_in']) * 0.9

    def __auth(self):
        if 'username' not in self.auth or 'password' not in self.auth:
            raise Exception("Must provide username and password in auth")

        if self.__is_oauth():
            self.r.set_oauth_app_info(client_id='a', client_secret='a', redirect_uri='a')
            self.__update_access_credentials()
        else:
            self.r.login(self.auth['username'], self.auth['password'])

    def __main(self):
        # Check if we need to update access token
        if time.time() > self.expires > 0:
            self.__update_access_credentials()

        # Get the content
        content = self._get_content()
        if not content:
            logger.warn('Bad content object: skipping...')
            return

        hits = 0
        misses = 0

        # Process all content
        for obj in content:
            # Check if it's in the cache
            if self.cache is not None:
                if obj.id in self.cache:
                    hits += 1
                    continue
                misses += 1
                self.cache[obj.id] = 0

            # Process the object, sandbox exceptions
            try:
                if not self._check(obj):
                    continue
                logger.info('Found valid object: {id} by {name}.'.format(id=obj.id,
                                                                         name=obj.author.name if obj.author else '[deleted]'))
                if not self._do(obj):
                    logger.info('Failed to process object {id}.'.format(id=obj.id))
            except Exception as e:
                logger.exception('Exception while processing object {id}'.format(id=obj.id))

        if self.cache is not None:
            logger.info('Cache hits/misses/total: {hits} / {misses} / {total}'.format(hits=hits, misses=misses,
                                                                                      total=hits + misses))

    def run(self):
        logger.info('Bot started!')

        while True:
            start_time = time.time()

            try:
                self.__main()
            except Exception as e:
                logger.exception('Exception while processing content generator')

            # Sleep at least self.delay per cycle
            time_delta = time.time() - start_time
            sleep_time = self.delay - time_delta
            logger.info('Processing/Sleeping for: {p:.2f}s / {s:.2f}s'.format(p=time_delta, s=max(0, sleep_time)))
            logger.info('Finished processing round for {name}'.format(name=self.user_agent))
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info('Bot finished! Exiting gracefully.')


class UserCommentsVoteTriggeredBot(BotHandler):
    def __init__(self, *args, **kwargs):
        self.monitored_user = kwargs.pop('monitored_user')
        self.score_threshold_max = kwargs.pop('score_threshold_max', None)
        self.score_threshold_min = kwargs.pop('score_threshold_min', None)
        if self.score_threshold_max is None and self.score_threshold_min is None:
            raise Exception("score_threshold_max or score_threshold_min should be set")

        super(UserCommentsVoteTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.r.get_redditor(self.monitored_user).get_comments(limit=self.fetch_limit)

    def _check(self, comment):
        # Check vote score min
        if self.score_threshold_min is not None and comment.score < self.score_threshold_min:
            return True

        # Check vote score max
        if self.score_threshold_max is not None and comment.score > self.score_threshold_max:
            return True

        return False


class MailTriggeredBot(BotHandler):
    def __init__(self, *args, **kwargs):
        super(MailTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.r.get_unread(limit=self.fetch_limit)

    def is_private_message(self, message):
        return not message.was_comment

    def is_comment_reply(self, message):
        return message.was_comment and message.subject == 'comment reply'

    def is_post_reply(self, message):
        return message.was_comment and message.subject == 'post reply'

    def is_username_mention(self, message):
        return message.was_comment and message.subject == 'username mention'


class SubredditCommentTriggeredBot(BotHandler):
    def __init__(self, *args, **kwargs):
        self.subreddit = kwargs.pop('subreddit')
        super(SubredditCommentTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.r.get_comments(self.subreddit, limit=self.fetch_limit)


class SubredditSubmissionTriggeredBot(BotHandler):
    def __init__(self, *args, **kwargs):
        self.subreddit = kwargs.pop('subreddit')
        super(SubredditSubmissionTriggeredBot, self).__init__(*args, **kwargs)

    def _get_content(self):
        return self.r.get_subreddit(self.subreddit).get_new(limit=self.fetch_limit)

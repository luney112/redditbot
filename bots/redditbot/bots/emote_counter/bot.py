from redditbot.base.handlers import MailTriggeredBot
import redditbot.base.utils as utils


class TopEmotesBot(MailTriggeredBot):
    def __init__(self, *args, **kwargs):
        super(TopEmotesBot, self).__init__(*args, **kwargs)

    def _check(self, mail):
        return self.is_private_message(mail)

    def _do(self, mail):
        reply_msg = '[](/sbstalkthread)This bot has been decommissioned.\n\n' \
                    'It has migrated over to [lunarmist.net](http://lunarmist.net/emotes/), ' \
                    'and has been enhanced with graphs and better comment coverage. Check it out!'

        # Reply to the user and mark it as read
        if utils.send_reply(mail, reply_msg):
            mail.mark_as_read()
            return True
        else:
            return False

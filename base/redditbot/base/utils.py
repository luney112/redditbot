import logging

import praw

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def has_replied(praw_object, username):
    """
    Returns True if the specified user has a comment in the top level replies of the given submission/comment/message,
    and False otherwise.
    For comments, submissions, messages ONLY.
    """
    if type(praw_object) == praw.objects.Message:
        # TODO: Fix this to actually check properly
        # If it's not the first message in the PM thread, we replied previously.
        # This is not the best method, and it is a bit flakey,
        # but good enough for most cases
        if praw_object.first_message is not None:
            return True
        return False
    elif type(praw_object) == praw.objects.Submission:
        praw_object.replace_more_comments(limit=None)
        replies = praw_object.comments
    elif type(praw_object) == praw.objects.Comment:
        replies = praw_object.replies
    else:
        raise Exception("Object must be an instance of praw.objects.Comment/Submission/Message")

    if not replies:
        return False

    # Check each reply if the username matches
    username = username.lower()
    for reply in replies:
        if reply.author and reply.author.name.lower() == username:
            return True

    return False


def is_comment_owner(praw_comment, username):
    """
    Returns True if the specified comment belongs to the user,
    otherwise False.
    """
    return praw_comment.author and praw_comment.author.name.lower() == username.lower()


def send_reply(praw_object, reply_msg):
    """
    Returns the reply object if the message was sent successfully, otherwise None.
    For comments, submissions, messages ONLY.
    """
    try:
        if type(praw_object) == praw.objects.Submission:
            reply_obj = praw_object.add_comment(reply_msg)
        else:
            reply_obj = praw_object.reply(reply_msg)
    except Exception as e:
        logger.exception('Exception while replying')
        return None

    logger.info(' => Reply Sent!')
    return reply_obj


def edit_reply(praw_comment, reply_msg):
    """
    Returns True if the comment was edited successfully, and False otherwise.
    For comments ONLY.
    """
    try:
        praw_comment.edit(reply_msg)
    except Exception as e:
        logger.exception('Exception while editing')
        return False

    logger.info(' => Edit was made!')
    return True


def has_chain(praw_r, praw_comment, username):
    """
    Returns True if the parent was made by username.
    Returns False otherwise.
    """
    if not hasattr(praw_comment, 'parent_id'):
        return False
    parent = praw_r.get_info(thing_id=praw_comment.parent_id)
    if not parent or type(parent) != praw.objects.Comment:
        return False
    return is_comment_owner(parent, username)


def is_transcript_reply(praw_r, praw_comment, username):
    if not hasattr(praw_comment, 'parent_id'):
        return False
    parent = praw_r.get_info(thing_id=praw_comment.parent_id)
    if not parent or type(parent) != praw.objects.Comment:
        return False
    return len(parent.body) > 50 and is_comment_owner(parent, username)

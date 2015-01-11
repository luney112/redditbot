REDDIT_ACCOUNTS = {
    'counts_your_emotes': {
        'username': '',
        'password': '',
    },
    'xkcd_transcriber': {
        'username': '',
        'password': '',
        'client_id': '',
        'secret': ''
    }
}

AUTHOR = '/u/name_here'

XKCD_DB_LOCATION = '/path/to/db'

try:
    from local_settings import *
except ImportError as e:
    pass

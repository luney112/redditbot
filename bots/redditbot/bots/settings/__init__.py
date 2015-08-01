import argparse
import logging

from base import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument('--settings', help='host', default='prod')

args, _ = parser.parse_known_args()

if args.settings == 'dev-mac':
    logger.info('Loading dev-mac settings')
    from dev_mac import *
elif args.settings == 'dev-win':
    logger.info('Loading dev-win settings')
    from dev_win import *
elif args.settings == 'prod':
    logger.info('Loading prod settings')
    from prod import *

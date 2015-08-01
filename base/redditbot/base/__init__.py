def patch_all():
    from gevent import monkey
    monkey.patch_all()

    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info('Monkey patching...')

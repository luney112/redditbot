def patch_all():
    print 'Monkey patching...'
    from gevent import monkey
    monkey.patch_all()

===============
Bets API client
===============

Installation
============

    pip install bets-api==0.0.1

Basic Usage
===========

.. code-block:: python

    import bets
    api = bets.BetsApi('<your token>')  # get token via admin UI

    bets = api.get_active_bets()  # list of active bets (same as on dashboard)
    len(bets)
    # => 70
    bets[13]
    # => {...} dict that represents the bet

    api.get_project_slug(bets[13])
    # => u'favim'

    api.stakes_in(bet[13])
    # => {'stakes': [{u'amount': Decimal('0.20000'),
    #      u'created': datetime.datetime(2014, 6, 2, 13, 36, 4, 322000),
    #      u'id': 3565,
    #      u'side': u'in',
    #      u'user': u'username'}],
    #    'sum': Decimal('0.20000')}

    api.stakes_out(bets[13])
    # => {'stakes': [], 'sum': 0}


Subscribe to Event.BET_EXPIRED
==============================

.. code-block:: python

    import bets
    import gevent
    api = bets.BetsApi('<your token>')

    def cb(bet):
        print 'Bet changed: [%s] %s' % (bet['id'], bet['description'])

    api.set_callback(bets.Event.BET_EXECUTED, cb)
    api.subscribe(bets.Event.BET_EXECUTED, [1020, 1009, 1010, 11])

    gevent.joinall(api.event_loop())
    # => Bet changed: [1009] [42-jobs] 0 bugs (2014-05-02 18:00)
    #    Bet changed: [1010] [coinhand] budget <= 400.0 (2014-04-30 11:15)
    #    Bet changed: [11] [kavyarnya] deadline <= 2014-03-01 (2014-02-14 02:00)

For more sophisticated example see `examples/`.

===============
Bets API client
===============

Installation
============

    pip install bets-api==0.0.4

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

    bets = api.get_active_bets(project_id=123)  # list of active bets filtered by project id
    len(bets)
    # => 20

    api.get_project_slug(bets[13])
    # => u'favim'

    api.stakes_in(bets[13])
    # => {'stakes': [{u'amount': Decimal('0.20000'),
    #      u'created': datetime.datetime(2014, 6, 2, 13, 36, 4, 322000),
    #      u'id': 3565,
    #      u'side': 0,
    #      u'user': u'username'}],
    #    'sum': Decimal('0.20000')}

    api.stakes_out(bets[13])
    # => {'stakes': [], 'sum': 0}


Creating bets
=============

.. code-block:: python

    api.create_budget(project_slug, expires_at, target_budget, bets_until, min_stake)
    # => {u'bet_id': 26, u'status': u'ok'}

- `expires_at`, `bets_until` - must be datetime objects
- `bets_until`, `min_stake` - not required

Also, there are methods for creating other types of bets:

.. code-block:: python

    create_no_bugs(self, project_slug, expires_at, bets_until=None, min_stake=None):
    create_budget(self, project_slug, expires_at, target_budget, bets_until=None, min_stake=None):
    create_deadline(self, project_slug, expires_at, target_deadline, bets_until=None, min_stake=None):
    create_human(self, description, expires_at, bets_until=None, min_stake=None):
    create_billable_hours(self, kava_username, expires_at, hours, start_date, end_date, bets_until=None, min_stake=None):
    create_closed_tickets(self, project_slug, expires_at, ticket_nums, bets_until=None, min_stake=None):
    create_fitting_budget(self, percent, expires_at, days=90, bets_until=None, min_stake=None):
    create_fitting_deadline(self, percent, expires_at, days=90, bets_until=None, min_stake=None):
    create_without_defects(self, percent, expires_at, days=90, bets_until=None, min_stake=None):
    create_estimate_ticket(self, project_slug, expires_at, ticket_num, bets_until=None, min_stake=None):


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

import sys
import bets
import gevent


def callback(bet):
    print u'Bet executed: [%s] %s' % (bet['id'], bet['description'])


def subscribe_active():
    while True:
        try:
            result = api.get_active_bets()
        except bets.ApiError as e:
            print 'Error %s' % e
            continue
        bet_ids = [b['id'] for b in result]
        api.subscribe(bets.Event.BET_EXECUTED, bet_ids)
        gevent.sleep(10)


if __name__ == '__main__':
    api = bets.BetsApi(sys.argv[1])
    api.set_callback(bets.Event.BET_EXECUTED, callback)
    threads = api.event_loop()
    threads.append(gevent.spawn(subscribe_active))
    gevent.joinall(threads)

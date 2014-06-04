__version__ = '0.0.2'

from gevent import monkey; monkey.patch_socket()

import re
import json
import datetime as dt
from urlparse import urljoin
from decimal import Decimal
from collections import defaultdict

import gevent
import requests


class ApiError(Exception):
    pass


class Event(object):
    BET_EXECUTED = 'bet_executed'


class BetsApi(object):
    '''API wrapper for bet engine.

    To use this you need to generate token (through admin UI) and then:

        api = bets.BetsApi('<your token>')
        api.get_active_bets()

    All entities (bets, stakes, etc) are represented as python dicts.
    Methods that take a bet or a stake as a parameters also rely on this.
    Generally, they assume that bet/stakes was returned by another API call,
    e.g. by get_active_bets().
    '''

    DEFAULT_SETTINGS = {
        'bets_url': u'http://bets.42cc.co',
        'timeout': 5,  # seconds
    }

    bet_types_with_project = [
        'budget',
        'deadline',
        '0_bugs',
        'closed_tickets',
    ]

    def __init__(self, token):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.settings['token'] = token

        self._callbacks = {}
        self._subscriptions = defaultdict(set)

    def _token_header(self):
        return {'Authorization': 'Token %s' % self.settings['token']}

    def _req(self, url):
        '''Make request and convert JSON response to python objects'''
        try:
            r = requests.get(
                url,
                headers=self._token_header(),
                timeout=self.settings['timeout'])
        except requests.exceptions.Timeout:
            raise ApiError('Request timed out (%s seconds)' % self.settings['timeout'])
        try:
            json = r.json()
        except ValueError:
            raise ApiError('Received not JSON response from API')
        if json.get('status') != 'ok':
            raise ApiError('API error: received unexpected json from API: %s' % json)
        return json

    def get_active_bets(self):
        '''Returns all active bets'''
        url = urljoin(
            self.settings['bets_url'],
            'bets?state=fresh,active,accept_end')
        return self._req(url)['bets']['results']

    def get_project_slug(self, bet):
        '''Return slug of a project that given bet is associated with
        or None if bet is not associated with any project.
        '''
        if bet.get('form_params'):
            params = json.loads(bet['form_params'])
            return params.get('project')
        return None

    def _convert_stake(self, stake):
        converted = stake.copy()
        converted['created'] = dt.datetime.strptime(
            stake['created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        converted['amount'] = Decimal(stake['amount'])
        return converted

    def _stakes_by_side(self, bet, side):
        stakes = [self._convert_stake(stake) for stake in bet['stakes']
                  if stake['side'] == side]
        result = {
            'stakes': stakes,
            'sum': sum([s['amount'] for s in stakes]),
        }
        return result

    def stakes_in(self, bet):
        '''Return all stakes on 'in' side for given bet.'''
        return self._stakes_by_side(bet, 'in')

    def stakes_out(self, bet):
        '''Return all stakes on 'out' side for given bet.'''
        return self._stakes_by_side(bet, 'out')

    def get_bets_by_ids(self, ids):
        ids = map(str, ids)
        url = urljoin(
            self.settings['bets_url'],
            'bets?id=%s' % ','.join(ids))
        return self._req(url)['bets']['results']

    def set_callback(self, event, callback):
        '''Set callback for event.

        Supported events: see `Event` class.

        Callback must take one parameter, which is a bet that changed.

        If callback is already set, it will be reset to a new value.
        '''
        self._callbacks[event] = callback

    def subscribe(self, event, bet_ids):
        '''Subscribe to event for given bet ids.'''
        if not self._subscriptions.get(event):
            self._subscriptions[event] = set()
        self._subscriptions[event] = self._subscriptions[event].union(bet_ids)

    def event_loop(self):
        '''Look for changes in bets, that user subscribed to by self.subscribe
        and trigger corresponding callbacks.
        '''
        return [gevent.spawn(self._poll_bet_executed)]

    def _poll_bet_executed(self):
        while True:
            if not self._subscriptions.get(Event.BET_EXECUTED):
                gevent.sleep(10)
                continue
            try:
                bets = self.get_bets_by_ids(self._subscriptions[Event.BET_EXECUTED])
            except ApiError as e:
                print '[ERROR] %s' % e
                continue
            executed_bets = [b for b in bets if b['state'] == 'executed']
            self._subscriptions[Event.BET_EXECUTED] -= set([b['id'] for b in executed_bets])
            callback = self._callbacks.get(Event.BET_EXECUTED)
            if callback:
                gevent.joinall([gevent.spawn(callback, b) for b in executed_bets])
            gevent.sleep(10)

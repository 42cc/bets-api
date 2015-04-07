__version__ = '0.0.8'

from gevent import monkey
monkey.patch_socket()
monkey.patch_ssl()
monkey.patch_time()

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
        'bets_url': u'http://bets.42cc.co/v1.1.3/',
        'timeout': 60,  # seconds
    }

    ACTIVE_STATES = ['fresh', 'active', 'accept_end']
    CLOSED_STATES = ['closed', 'executed', 'calculated', 'returned']

    TIME_FMT = '%Y-%m-%d %H:%M'
    DATE_FMT = '%Y-%m-%d'

    SIDE_IN = 0
    SIDE_OUT = 1

    def __init__(self, token):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.settings['token'] = token

        self._callbacks = {}
        self._subscriptions = defaultdict(set)

    def _token_header(self):
        return {'Authorization': 'Token %s' % self.settings['token']}

    def _req(self, url, method='GET', **kw):
        '''Make request and convert JSON response to python objects'''
        send = requests.post if method == 'POST' else requests.get
        try:
            r = send(
                url,
                headers=self._token_header(),
                timeout=self.settings['timeout'],
                **kw)
        except requests.exceptions.Timeout:
            raise ApiError('Request timed out (%s seconds)' % self.settings['timeout'])
        try:
            json = r.json()
        except ValueError:
            raise ApiError('Received not JSON response from API')
        if json.get('status') != 'ok':
            raise ApiError('API error: received unexpected json from API: %s' % json)
        return json

    def get_active_bets(self, project_id=None):
        '''Returns all active bets'''
        url = urljoin(
            self.settings['bets_url'],
            'bets?state=fresh,active,accept_end&page=1&page_size=100')

        if project_id is not None:
            url += '&kava_project_id={}'.format(project_id)

        bets = []
        has_next_page = True
        while has_next_page:
            res = self._req(url)
            bets.extend(res['bets']['results'])
            url = res['bets'].get('next')
            has_next_page = bool(url)

        return bets

    def get_bets(self, type=None, order_by=None, state=None, page=None, page_size=None):
        """Return bets with given filters and ordering.

        :param type: return bets only with this type.
                     Use None to include all (default).
        :param order_by: '-last_stake' or 'last_stake' to sort by stake's
                         created date or None for default ordering.
        :param state: one of 'active', 'closed', 'all' (default 'active').
        :param page: default 1.
        :param page_site: page size (default 100).
        """
        if page is None:
            page = 1
        if page_size is None:
            page_size = 100
        if state == 'all':
            _states = []  # all states == no filter
        elif state == 'closed':
            _states = self.CLOSED_STATES
        else:
            _states = self.ACTIVE_STATES

        url = urljoin(
            self.settings['bets_url'],
            'bets?page={}&page_size={}'.format(page, page_size))
        url += '&state={}'.format(','.join(_states))
        if type is not None:
            url += '&type={}'.format(type)
        if order_by in ['-last_stake', 'last_stake']:
            url += '&order_by={}'.format(order_by)

        res = self._req(url)
        return res['bets']['results']

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
        return self._stakes_by_side(bet, self.SIDE_IN)

    def stakes_out(self, bet):
        '''Return all stakes on 'out' side for given bet.'''
        return self._stakes_by_side(bet, self.SIDE_OUT)

    def get_bets_by_ids(self, ids):
        ids = map(str, ids)
        url = urljoin(
            self.settings['bets_url'],
            'bets?id=%s' % ','.join(ids))
        return self._req(url)['bets']['results']

    def _create(self, url, data, expires_at, bets_until=None, min_stake=None,
                group=None):
        url = urljoin(self.settings['bets_url'], url)
        data = data.copy()
        data['expires'] = expires_at.strftime(self.TIME_FMT)
        if group is not None:
            data['group'] = group
        if bets_until is not None:
            data['stakes_acception_end'] = bets_until.strftime(self.TIME_FMT)
        if min_stake is not None:
            if len(min_stake) == 2:
                data['min_in'], data['min_out'] = min_stake
            elif len(min_stake) == 6:
                (data['less_1cp'], data['equal_1cp'], data['equal_2cp'],
                 data['equal_3cp'], data['equal_4cp'], data['more_4cp']) = min_stake
        return self._req(url, 'POST', data=data)

    def create_no_bugs(self, project_slug, expires_at, bets_until=None,
                       min_stake=None, group=None):
        url = 'bet/create/no-bugs'
        data = {'project': project_slug}
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_commit_bugs(self, project_slug, commit_hash, expires_at,
                           bets_until=None, min_stake=None, group=None):
        url = 'bet/create/commit_bug'
        data = {
            'project': project_slug,
            'commit_hash': commit_hash,
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_budget(self, project_slug, expires_at, target_budget,
                      bets_until=None, min_stake=None, group=None):
        url = 'bet/create/budget'
        data = {
            'project': project_slug,
            'goal': target_budget,
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_deadline(self, project_slug, expires_at, target_deadline,
                        bets_until=None, min_stake=None, group=None):
        url = 'bet/create/deadline'
        data = {
            'project': project_slug,
            'goal': target_deadline.strftime(self.DATE_FMT),
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_human(self, description, expires_at, bets_until=None,
                     min_stake=None, group=None):
        url = 'bet/create/human'
        data = {'description': description}
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_billable_hours(self, kava_username, expires_at, hours, start_date, end_date,
                              bets_until=None, min_stake=None, group=None):
        url = 'bet/create/billable'
        data = {
            'user': kava_username,
            'goal': hours,
            'start_date': start_date.strftime(self.DATE_FMT),
            'end_date': end_date.strftime(self.DATE_FMT),
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_closed_tickets(self, project_slug, expires_at, ticket_nums,
                              bets_until=None, min_stake=None, group=None):
        url = 'bet/create/closed_tickets'
        if not isinstance(ticket_nums, list):
            ticket_nums = [ticket_nums]
        data = {
            'project': project_slug,
            'tickets': ','.join(map(str, ticket_nums)),
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_fitting_budget(self, percent, expires_at, days=90,
                              bets_until=None, min_stake=None, group=None):
        url = 'bet/create/fitting_budget'
        data = {
            'percent': percent,
            'last_N_days': days,
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_fitting_deadline(self, percent, expires_at, days=90,
                                bets_until=None, min_stake=None, group=None):
        url = 'bet/create/fitting_deadline'
        data = {
            'percent': percent,
            'last_N_days': days,
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_without_defects(self, percent, expires_at, days=90,
                               bets_until=None, min_stake=None, group=None):
        url = 'bet/create/without_defects'
        data = {
            'percent': percent,
            'last_N_days': days,
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

    def create_estimate_ticket(self, project_slug, expires_at, ticket_num,
                               bets_until=None, min_stake=None, group=None):
        url = 'bet/create/estimate_ticket'
        data = {
            'project': project_slug,
            'ticket': ticket_num,
        }
        return self._create(url, data, expires_at, bets_until, min_stake, group)

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

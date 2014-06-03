import re
import json
import datetime as dt
from urlparse import urljoin
from decimal import Decimal

import requests


class ApiError(Exception):
    pass


class BetsApi(object):

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
        if json['status'] != 'ok':
            raise ApiError('API error: %s' % json['status'])
        return json

    def get_active_bets(self):
        url = urljoin(
            self.settings['bets_url'],
            'bets?state=fresh,active,accept_end')
        return self._req(url)['bets']['results']

    def get_project_slug(self, bet):
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
        return self._stakes_by_side(bet, 'in')

    def stakes_out(self, bet):
        return self._stakes_by_side(bet, 'out')

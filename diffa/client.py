import datetime
import json
import logging
import sys
from restful_lib import Connection
from urlparse import urljoin

DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'

def strftime(time):
    "Format datetime strings in the format required by the agent"
    return time.strftime(DATETIME_FORMAT)

def strptime(time):
    "Parse datetime strings in the format required by the agent"
    return datetime.datetime.strptime(time, DATETIME_FORMAT)

class DiffsClient(object):

    _logger = logging.getLogger('DiffsClient')
    _logger.addHandler(logging.StreamHandler(sys.stderr))

    def __init__(self, agent_url, verbose=False):
        self._logger.setLevel(logging.DEBUG if verbose else logging.NOTSET)
        if not agent_url.endswith('/'):
            agent_url += '/'
        self.agent_url = agent_url
        base_url = urljoin(agent_url, 'rest')
        self._conn = Connection(base_url)
        self._conn = Connection(self.get_session_url())

    def get_session_url(self):
        url = '/diffs/sessions'
        response = self._post(url)
        return response['headers']['location']

    def get_diffs(self, pair_key, range_start, range_end):
        url = '/?pairKey={0}&range-start={1}&range-end={2}'.format(
                pair_key,
                range_start.strftime(DATETIME_FORMAT),
                range_end.strftime(DATETIME_FORMAT))
        response = self._get(url)
        return json.loads(response['body'])

    def get_diffs_zoomed(self, range_start, range_end, bucketing):
        "A dictionary of pair keys mapped to lists of bucketed diffs"
        url = '/zoom?range-start={0}&range-end={1}&bucketing={2}'.format(
                range_start.strftime(DATETIME_FORMAT),
                range_end.strftime(DATETIME_FORMAT),
                bucketing)
        response = self._get(url)
        return json.loads(response['body'])

    def _get(self, url):
        self._logger.debug("GET %s", self._rebuild_url(url))
        response = self._conn.request_get(url)
        self._logger.debug(response)
        return response
    
    def _post(self, url):
        self._logger.debug("POST %s", self._rebuild_url(url))
        response = self._conn.request_post(url)
        self._logger.debug(response)
        return response

    def _rebuild_url(self, url):
        return self._conn.url.geturl() + url

    def __repr__(self):
        return "DiffsClient(%s)" % repr(self.agent_url)


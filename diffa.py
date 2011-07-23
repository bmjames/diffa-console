#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import datetime
import logging
from restful_lib import Connection
import sys
from urlparse import urljoin

DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'

LIGHT_SHADE = u'░'
MED_SHADE = u'▒'
DARK_SHADE = u'▓'

DEFAULT_WIDTH = 80
LABEL_WIDTH = 10

class DiffsClient(object):

    _logger = logging.getLogger('DiffsClient')
    _logger.addHandler(logging.StreamHandler(sys.stderr))

    def __init__(self, agent_url, verbose=False):
        self._logger.setLevel(logging.DEBUG if verbose else logging.NOTSET)
        if agent_url[-1] != "/":
            agent_url += "/"
        self.agent_url = agent_url
        base_url = urljoin(agent_url, 'rest')
        self.conn = Connection(base_url)
        self.conn = Connection(self.get_session_url())

    def get_session_url(self):
        url = '/diffs/sessions'
        self._logger.debug("Getting session URL from %s", self._rebuild_url(url))
        response = self.conn.request_post(url)
        self._logger.debug("Got response: %s", response)
        return response['headers']['location']

    def get_diffs(self, range_start, range_end, bucketing):
        "A dictionary of pair keys mapped to lists of bucketed diffs"
        url = '/zoom?range-start={0}&range-end={1}&bucketing={2}'.format(
                range_start.strftime(DATETIME_FORMAT),
                range_end.strftime(DATETIME_FORMAT),
                bucketing)
        self._logger.debug("Getting diffs from %s", self._rebuild_url(url))
        response = self.conn.request_get(url)
        self._logger.debug("Got response: %s", response)
        return json.loads(response['body'])

    def _rebuild_url(self, url):
        return self.conn.url.geturl() + url

    def __repr__(self):
        return "DiffsClient(%s)" % repr(self.agent_url)

def format_y_label(pair_key, width=LABEL_WIDTH):
    return pair_key[0:width-1].ljust(width)

def format_x_label(time, width=LABEL_WIDTH):
    return time.strftime("|%H:%M")[0:width].ljust(width)

def round_down_to_hour(date_time):
    return date_time.replace(minute=0, second=0)

def round_up_to_hour(date_time):
    return round_down_to_hour(date_time) + datetime.timedelta(hours=1)    

def shade(count):
    if not count:
        return " "
    if count < 3:
        return LIGHT_SHADE
    if count < 10:
        return MED_SHADE
    return DARK_SHADE

def show_heatmap(client, start_time, end_time, width):
    bucketing = calculate_bucketing(width, start_time, end_time)
    diffs = client.get_diffs(start_time, end_time, bucketing)

    swimlane_boundary = "-" * width
    print_time_axis(width, start_time, end_time)
    for pair_key, diffs in diffs.iteritems():
        print swimlane_boundary
        print format_y_label(pair_key) + "".join(shade(count) for count in diffs)
    print swimlane_boundary

def print_time_axis(width, start_time, end_time):
    heatmap_width = width - LABEL_WIDTH # allow for y-axis labels
    timespan = end_time - start_time
    time_per_char = timespan / heatmap_width
    line = " " * LABEL_WIDTH
    for i in xrange(heatmap_width / LABEL_WIDTH):
        time = start_time + i * (time_per_char * LABEL_WIDTH)
        line += format_x_label(time)
    print line

def calculate_bucketing(width, start_time, end_time):
    heatmap_width = width - LABEL_WIDTH # allow for y-axis labels
    timespan = end_time - start_time
    return int((timespan / heatmap_width).total_seconds())

def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Console UI for Diffa')
    add_arg = parser.add_argument

    add_arg('agent_url', metavar='URL', type=str, help='the base URL of the agent')

    default_end_time = round_up_to_hour(datetime.datetime.utcnow())
    default_start_time = default_end_time - datetime.timedelta(hours=21)
    add_arg('--from', dest='start_time', metavar='FROM',
            type=str, default=default_start_time.strftime(DATETIME_FORMAT),
            help='show diffs from this UTC time (default: 21 hours before FROM)')
    add_arg('--until', dest='end_time', metavar='UNTIL', type=str,
            default=default_end_time.strftime(DATETIME_FORMAT),
            help='show diffs until this UTC time (default: now)')

    add_arg('-w', dest='width', metavar='WIDTH', type=int, default=DEFAULT_WIDTH,
            help='width (in characters) of output (default: 80)')
    add_arg('-v', dest='verbose', action='store_true', help='show HTTP activity')

    args = parser.parse_args()

    client = DiffsClient(args.agent_url, args.verbose)
    
    start_time = datetime.datetime.strptime(args.start_time, DATETIME_FORMAT)
    end_time = datetime.datetime.strptime(args.end_time, DATETIME_FORMAT)
    show_heatmap(client, start_time, end_time, args.width)

if __name__ == '__main__':
    main()

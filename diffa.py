#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import datetime
import logging
from restful_lib import Connection
import sys
from urlparse import urljoin

DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'

SHADE_THRESHOLDS = {
    1: u'░',
    4: u'▒',
    10: u'▓'
}

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
            
def list_diffs(args):
    client = DiffsClient(args.agent_url, args.verbose)
    
    start_time = datetime.datetime.strptime(args.start_time, DATETIME_FORMAT)
    end_time = datetime.datetime.strptime(args.end_time, DATETIME_FORMAT)
    
    diffs = client.get_diffs(args.pair_key, start_time, end_time)
    for diff in diffs:
        data = (describe_match_state(diff),
                diff['objId']['id'],
                diff['upstreamVsn'],
                diff['downstreamVsn'],
                diff['detectedAt'])
        print " ".join(unicode(datum) or "-" for datum in data)
        
def describe_match_state(entity):
    "md (missing from downstream), mu (missing from upstream) or dd (data diff)"
    if entity['downstreamVsn'] is None:
        return "md"
    if entity['upstreamVsn'] is None:
        return "mu"
    return "dd"

def format_y_label(pair_key, width=LABEL_WIDTH):
    return pair_key[0:width-1].ljust(width)

def format_x_label(time, width=LABEL_WIDTH):
    return time.strftime("|%H:%M")[0:width].ljust(width)

def round_down_to_hour(date_time):
    return date_time.replace(minute=0, second=0)

def round_up_to_hour(date_time):
    return round_down_to_hour(date_time) + datetime.timedelta(hours=1)    

def shade(count):
    for threshold, char in reversed(sorted(SHADE_THRESHOLDS.iteritems())):
        if count >= threshold:
            return char
    return " "

def show_heatmap(args):
    client = DiffsClient(args.agent_url, args.verbose)
    
    start_time = datetime.datetime.strptime(args.start_time, DATETIME_FORMAT)
    end_time = datetime.datetime.strptime(args.end_time, DATETIME_FORMAT)
    bucketing = calculate_bucketing(args.width, start_time, end_time)
    diffs = client.get_diffs_zoomed(start_time, end_time, bucketing)

    swimlane_boundary = "-" * args.width
    print_time_axis(args.width, start_time, end_time)
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

def add_common_args_to(parser):
    add_arg = parser.add_argument
    
    default_end_time = round_up_to_hour(datetime.datetime.utcnow())
    default_start_time = default_end_time - datetime.timedelta(hours=21)
    add_arg('agent_url', metavar='AGENT', help='the base URL of the agent')
    add_arg('--from', dest='start_time', metavar='FROM',
            type=str, default=default_start_time.strftime(DATETIME_FORMAT),
            help='show diffs from this UTC time (default: 21 hours ago)')
    add_arg('--until', dest='end_time', metavar='UNTIL',
            default=default_end_time.strftime(DATETIME_FORMAT),
            help='show diffs until this UTC time (default: now)')

    add_arg('-v', dest='verbose', action='store_true', help='show HTTP activity')

def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Console UI for Diffa')
    subparsers = parser.add_subparsers(help='sub-command')

    heatmap_parser = subparsers.add_parser('heatmap',
            help='show differences heatmap')
    heatmap_parser.set_defaults(func=show_heatmap)
    add_common_args_to(heatmap_parser)
    heatmap_parser.add_argument('-w', dest='width', metavar='WIDTH', type=int,
            default=DEFAULT_WIDTH,
            help='width (in characters) of output (default: 80)')

    diffs_parser = subparsers.add_parser('diffs', help='list diffs')
    diffs_parser.set_defaults(func=list_diffs)
    add_common_args_to(diffs_parser)
    diffs_parser.add_argument('pair_key', metavar='PAIR', help='pair key')

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()


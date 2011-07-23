#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import datetime
from restful_lib import Connection
from urlparse import urljoin

DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'

LIGHT_SHADE = u'░'
MED_SHADE = u'▒'
DARK_SHADE = u'▓'

DEFAULT_WIDTH = 80
LABEL_WIDTH = 10

class DiffsClient(object):
    def __init__(self, agent_url):
        if agent_url[-1] != "/":
            agent_url += "/"
        self.agent_url = agent_url
        base_url = urljoin(agent_url, 'rest')
        self.conn = Connection(base_url)
        self.session_url = self.get_session_url()
        self.conn = Connection(self.session_url)

    def get_session_url(self):
        response = self.conn.request_post('/diffs/sessions')
        return response['headers']['location']

    def get_diffs(self, range_start, range_end, bucketing):
        "A dictionary of pair keys mapped to lists of bucketed diffs"
        url = '/zoom?range-start={0}&range-end={1}&bucketing={2}'.format(
                range_start.strftime(DATETIME_FORMAT),
                range_end.strftime(DATETIME_FORMAT),
                bucketing)
        response = self.conn.request_get(url)
        return json.loads(response['body'])

    def __repr__(self):
        return "DiffsClient(%s)" % repr(self.agent_url)

def format_y_label(pair_key, width=LABEL_WIDTH):
    return pair_key[0:width-1].ljust(width)

def format_x_label(time, width=LABEL_WIDTH):
    return time.strftime("%H:%M >")[0:width].rjust(width)

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
    line = format_x_label(start_time)
    for i in xrange(heatmap_width / LABEL_WIDTH):
        time = start_time + (i + 1) * (time_per_char * LABEL_WIDTH)
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
            help='character width of output (default: 80)')

    args = parser.parse_args()

    client = DiffsClient(args.agent_url)
    
    start_time = datetime.datetime.strptime(args.start_time, DATETIME_FORMAT)
    end_time = datetime.datetime.strptime(args.end_time, DATETIME_FORMAT)
    show_heatmap(client, start_time, end_time, args.width)

if __name__ == '__main__':
    main()


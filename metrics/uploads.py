#!/usr/bin/env python3
"""Generate daily upload report.

Copyright 2017 Canonical Ltd.
Robbie Basak <robie.basak@canonical.com>
Joshua Powers <josh.powers@canonical.com>
"""
import argparse

from datetime import datetime

from prometheus_client import CollectorRegistry, Gauge

from metrics.helpers import lp
from metrics.helpers import util


def print_result(upload, category):
    """Print result of algorthm."""
    print('%s: %s %s %s %s %s' % (category, upload['package'],
                                  upload['version'], upload['series'],
                                  upload['pocket'], upload['sponsor']))


def generate_upload_report(date):
    """Given a date, get uploads for that day."""
    results = {'dev': 0, 'sru': 0}

    packages = util.get_team_packages()
    ubuntu = lp.get_ubuntu()
    devels = ubuntu.getDevelopmentSeries()
    assert len(devels) == 1
    devel = devels[0].name
    archive = ubuntu.main_archive

    for package in packages:
        spphs = archive.getPublishedSources(
            created_since_date=date,
            # essential ordering for migration detection
            order_by_date=True,
            source_name=package,
            exact_match=True,
        )

        for spph in spphs:
            upload = {
                'package': spph.source_package_name,
                'version': spph.source_package_version,
                'series': lp.get_series_name(spph.distro_series_link),
                'sponsor': lp.get_person_name(spph.sponsor_link),
                'pocket': spph.pocket,
            }

            if upload['series'] == devel:
                if upload['pocket'] == 'Release':
                    # sucessful publish to devel release
                    results['dev'] = results['dev'] + 1
                    print_result(upload, 'dev')
            else:
                if upload['pocket'] == 'Updates':
                    # sucessful SRU migration
                    results['sru'] = results['sru'] + 1
                    print_result(upload, 'sru')

    return results


def collect(dryrun=False):
    """Push upload data."""
    date = datetime.now().date().strftime('%Y-%m-%d')
    results = generate_upload_report(date)
    print('%s: %s' % (date, results))

    if not dryrun:
        print('Pushing data...')
        registry = CollectorRegistry()

        Gauge('server_uploads_daily_dev_total',
              'Uploads to dev release',
              None,
              registry=registry).set(results['dev'])

        Gauge('server_uploads_daily_sru_total',
              'Uploads to supported release (SRU)',
              None,
              registry=registry).set(results['sru'])

        util.push2gateway('upload', registry)


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--dryrun', action='store_true')
    ARGS = PARSER.parse_args()
    collect(ARGS.dryrun)

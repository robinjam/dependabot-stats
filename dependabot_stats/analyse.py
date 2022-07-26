from collections import namedtuple
import csv
from datetime import datetime, timedelta, timezone
from itertools import groupby
import dateutil.parser
import urllib.request, json


PullRequest = namedtuple('PullRequest', ['repo', 'library', 'opened_at', 'closed_at', 'duration', 'is_security'])


def read_pull_requests(filename, ignore_libraries=[]):
    def parse_row(row):
        library = row['library']
        if library in ignore_libraries:
            return

        opened_at = dateutil.parser.isoparse(row['opened_at'])
        closed_at = dateutil.parser.isoparse(row['closed_at'])
        if opened_at < datetime(2020, 6, 11, tzinfo=timezone.utc):
            # Ignore PRs opened before RFC 126 was published
            return
        duration = closed_at - opened_at
        is_security = row['is_security'] == 'true'
        return PullRequest(row['repo'], row['library'], opened_at, closed_at, duration, is_security)

    with open(filename, newline='') as file:
        reader = csv.DictReader(file)
        return [parse_row(row) for row in reader if parse_row(row)]


def print_basic_pr_stats(pull_requests):
    print('Total PRs:', len(pull_requests))
    print('Mean time to merge:', sum([pr.duration for pr in pull_requests], timedelta()) / len(pull_requests))
    print('Max time to merge:', max([pr.duration for pr in pull_requests]))


def print_pr_stats(pull_requests):
    prs_grouped_by_library = {
        library: list(prs)
        for library, prs in groupby(pull_requests, key=lambda pr: pr.library)
    }

    mean_grouped_by_library = {
        library: sum([pr.duration for pr in prs], timedelta()) / len(prs)
        for library, prs in prs_grouped_by_library.items()
    }

    libraries_ordered_by_mean_duration = {
        k: v for k, v in sorted(mean_grouped_by_library.items(), key=lambda item: item[1], reverse=True)
    }

    libraries_with_duration = [
        f'{library} ({duration})'
        for library, duration in libraries_ordered_by_mean_duration.items()
    ]

    print_basic_pr_stats(pull_requests)
    print('Top 5 longest libraries to merge:', ', '.join(libraries_with_duration[:5]))
    print('Top 5 quickest libraries to merge:', ', '.join(libraries_with_duration[-5:]))


def print_all_pr_stats(pull_requests):
    print('All PRs')
    print('=======')
    print_pr_stats(pull_requests)
    print()

    print('Security PRs')
    print('============')
    print_pr_stats([pr for pr in pull_requests if pr.is_security])
    print()

    print('Non-security PRs')
    print('================')
    print_pr_stats([pr for pr in pull_requests if not pr.is_security])


def print_library_stats(pull_requests, internal_libraries, framework_libraries):
    security_prs = [pr for pr in pull_requests if pr.is_security]
    internal_prs = [pr for pr in pull_requests if pr.library in internal_libraries]
    framework_prs = [pr for pr in pull_requests if pr.library in framework_libraries]
    other_prs = [
        pr for pr in pull_requests
        if not pr.is_security and not pr.library in internal_libraries and not pr.library in framework_libraries
    ]

    print('Security Libraries')
    print('==================')
    print_pr_stats(security_prs)
    print()

    print('Internal Libraries')
    print('==================')
    print_pr_stats(internal_prs)
    print()

    print('Framework Libraries')
    print('===================')
    print_pr_stats(framework_prs)
    print()

    print('Third Party Libraries (Framework + Ignored)')
    print('===========================================')
    print_pr_stats(framework_prs + other_prs)
    print()

    print('All Allowed Libraries (Security + Internal + Framework)')
    print('=======================================================')
    print_pr_stats(security_prs + internal_prs + framework_prs)
    print()

    print('Ignored Libraries')
    print('=================')
    print_pr_stats(other_prs)

def fetch_govuk_repos():
    with urllib.request.urlopen("https://docs.publishing.service.gov.uk/repos.json") as connection:
        return json.load(connection)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data.csv')
    parser.add_argument('--ignore-library', '-l', nargs='*', default=['urllib3', 'notebook'])

    subparsers = parser.add_subparsers()
    parser_prs = subparsers.add_parser('prs')
    parser_prs.set_defaults(func=print_all_pr_stats)

    parser_libraries = subparsers.add_parser('libraries')
    parser_libraries.add_argument('--internal-libraries', '-i', nargs='*', default=[repo['app_name'] for repo in fetch_govuk_repos()])
    parser_libraries.add_argument('--framework-libraries', '-f', nargs='*', default=['factory_bot_rails', 'jasmine', 'rails', 'rspec-rails', 'sass-rails'])
    parser_libraries.set_defaults(func=print_library_stats)

    args = parser.parse_args()

    if 'func' in args:
        pull_requests = read_pull_requests(args.input, ignore_libraries=args.ignore_library)
        if args.func == print_all_pr_stats:
            print_all_pr_stats(pull_requests)
        elif args.func == print_library_stats:
            print_library_stats(pull_requests, args.internal_libraries, args.framework_libraries)
    else:
        parser.print_help()

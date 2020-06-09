from collections import namedtuple
import csv
from datetime import datetime, timedelta
from itertools import groupby


PullRequest = namedtuple('PullRequest', ['repo', 'library', 'opened_at', 'closed_at', 'duration', 'is_security'])


def read_pull_requests(filename, ignore_libraries=[]):
    def parse_row(row):
        library = row['library']
        if library in ignore_libraries:
            return

        opened_at = datetime.fromisoformat(row['opened_at'])
        closed_at = datetime.fromisoformat(row['closed_at'])
        duration = closed_at - opened_at
        is_security = row['is_security'] == 'true'
        return PullRequest(row['repo'], row['library'], opened_at, closed_at, duration, is_security)

    with open(filename, newline='') as file:
        reader = csv.DictReader(file)
        return [parse_row(row) for row in reader if parse_row(row)]


def print_stats(pull_requests):
    print('Mean time to merge:', sum([pr.duration for pr in pull_requests], timedelta()) / len(pull_requests))
    print('Max time to merge:', max([pr.duration for pr in pull_requests]))

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

    print('Top 5 longest libraries to merge:', ', '.join(libraries_with_duration[:5]))
    print('Top 5 quickest libraries to merge:', ', '.join(libraries_with_duration[-5:]))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data.csv')
    parser.add_argument('--ignore-library', '-l', nargs='*')

    args = parser.parse_args()

    pull_requests = read_pull_requests(args.input, ignore_libraries=args.ignore_library)

    print('All PRs')
    print('=======')
    print_stats(pull_requests)
    print()

    print('Security PRs')
    print('============')
    print_stats([pr for pr in pull_requests if pr.is_security])
    print()

    print('Non-security PRs')
    print('================')
    print_stats([pr for pr in pull_requests if not pr.is_security])

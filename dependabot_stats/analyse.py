from collections import namedtuple
import csv
from datetime import datetime, timedelta


PullRequest = namedtuple('PullRequest', ['repo', 'opened_at', 'closed_at', 'duration', 'is_security'])


def read_pull_requests(filename):
    def parse_row(row):
        opened_at = datetime.fromisoformat(row['opened_at'])
        closed_at = datetime.fromisoformat(row['closed_at'])
        duration = closed_at - opened_at
        is_security = row['is_security'] == 'true'
        return PullRequest(row['repo'], opened_at, closed_at, duration, is_security)

    with open(filename, newline='') as file:
        reader = csv.DictReader(file)
        return [parse_row(row) for row in reader]


def print_stats(pull_requests):
    print('Mean:', sum([pr.duration for pr in pull_requests], timedelta()) / len(pull_requests))
    print('Max:', max([pr.duration for pr in pull_requests]))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data.csv')

    args = parser.parse_args()

    pull_requests = read_pull_requests(args.input)

    print('All PRs')
    print_stats(pull_requests)
    print()

    print('Security PRs')
    print_stats([pr for pr in pull_requests if pr.is_security])
    print()

    print('Non-security PRs')
    print_stats([pr for pr in pull_requests if not pr.is_security])

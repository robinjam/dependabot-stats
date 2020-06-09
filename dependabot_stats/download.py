from collections import namedtuple
import csv
import os
import time

from github import Github


PullRequest = namedtuple('PullRequest', ['repo', 'opened_at', 'closed_at', 'is_security'])

github = Github(os.environ['GITHUB_TOKEN'], per_page=100)



def download_repos(user, topic):
    query = f'user:{user} topic:{topic} archived:false'
    return sorted(repo.full_name for repo in github.search_repositories(query=query))


def download_pull_requests(user, repos):
    for i, repo in enumerate(repos):
        print('Downloading:', repo, f'{i}/{len(repos)}')

        query = f'repo:{repo} author:app/dependabot author:app/dependabot-preview is:pr is:merged'

        for issue in github.search_issues(query=query):
            is_security = any(label.name == 'security' for label in issue.labels)
            yield PullRequest(repo, issue.created_at, issue.closed_at, is_security)

        time.sleep(1)  # for GitHub Search API rate limiting


def write_pull_requests(pull_requests, filename):
    with open(filename, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['repo', 'opened_at', 'closed_at', 'is_security'])

        writer.writeheader()

        for pull_request in pull_requests:
            writer.writerow({
                'repo': pull_request.repo,
                'opened_at': pull_request.opened_at.isoformat(),
                'closed_at': pull_request.closed_at.isoformat(),
                'is_security': 'true' if pull_request.is_security else 'false',
            })


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='alphagov')
    parser.add_argument('--topic', default='govuk')
    parser.add_argument('--output', default='data.csv')

    args = parser.parse_args()

    print(github.get_rate_limit())

    repos = download_repos(args.user, args.topic)
    print(len(repos), 'repos to download')

    pull_requests = download_pull_requests(args.user, repos)
    write_pull_requests(pull_requests, args.output)

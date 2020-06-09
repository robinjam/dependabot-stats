from collections import namedtuple
import csv
import os
import re
import time

from github import Github


PullRequest = namedtuple('PullRequest', ['repo', 'library', 'opened_at', 'closed_at', 'is_security'])

github = Github(os.environ['GITHUB_TOKEN'], per_page=100)



def download_repos(user, topic):
    query = f'user:{user} topic:{topic} archived:false'
    return sorted(repo.full_name for repo in github.search_repositories(query=query))


def download_pull_requests(user, repos):
    def extract_library(title):
        if not ('Bump' in title or 'bump' in title):
            return  # sometimes PR titles get edited by other people

        match = re.search(r'bump ([a-zA-Z0-9-_@/]*)(,| from| and)', title, re.IGNORECASE)
        if match:
            return match.group(1)

        raise RuntimeError(f'Could not extract library from "{title}"')

    for i, repo in enumerate(repos):
        print('Downloading:', repo, f'{i}/{len(repos)}')

        query = f'repo:{repo} author:app/dependabot author:app/dependabot-preview is:pr is:merged'

        for issue in github.search_issues(query=query):
            library = extract_library(issue.title)
            if library is None:
                continue

            is_security = any(label.name == 'security' for label in issue.labels)
            yield PullRequest(repo, library, issue.created_at, issue.closed_at, is_security)

        time.sleep(2)  # for GitHub Search API rate limiting


def write_pull_requests(pull_requests, filename):
    with open(filename, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['repo', 'library', 'opened_at', 'closed_at', 'is_security'])

        writer.writeheader()

        for pull_request in pull_requests:
            writer.writerow({
                'repo': pull_request.repo,
                'library': pull_request.library,
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

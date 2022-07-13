require "csv"
require "octokit"

def extract_library_name(title)
  if title == "Upgrade to GitHub-native Dependabot"
    nil
  elsif /\AUpdate .+ requirement from .+ to .+\z/.match?(title)
    nil
  elsif matches = /[Bb]ump (.+) from .+ to .+\z/.match(title)
    matches[1]
  elsif matches = /[Bb]ump (.+ and .+)\z/.match(title)
    # This will match e.g. "foo, bar and baz" and return ["foo", "bar", "baz"]
    matches[1].split(/, | and /)[0]
  else
    STDERR.puts "Warning: Could not extract library name(s) from pull request title \"#{title}\""
    nil
  end
end

# Rewrites X-RateLimit headers so that the Faraday::Retry::Middleware can read them and
# automatically wait until the rate limit expires before retrying
class RewriteRateLimitHeaders < Faraday::Middleware
  def initialize(app)
    super(app)
    @app = app
  end

  def call(request_env)
    @app.call(request_env).on_complete do |response_env|
      headers = response_env[:response_headers]
      if headers.include? 'X-RateLimit-Limit'
        headers['RateLimit-Limit'] = headers['X-RateLimit-Limit']
      end
      if headers.include? 'X-RateLimit-Remaining'
        headers['RateLimit-Remaining'] = headers['X-RateLimit-Remaining']
      end
      if headers.include? 'X-RateLimit-Reset'
        # X-RateLimit-Reset is a timestamp (i.e. the number of seconds since epoch)
        # RateLimit-Reset is expected to be in RFC2822 format
        limit_expires_at = headers['RateLimit-Reset'] = Time.at(headers['X-RateLimit-Reset'].to_i).rfc2822

        if headers['RateLimit-Remaining'] == '0'
          STDERR.puts "Warning: Rate limited until #{limit_expires_at}"
        end
      end
    end
  end
end

stack = Faraday::RackBuilder.new do |builder|
  builder.use Faraday::Retry::Middleware, { exceptions: Octokit::TooManyRequests }
  builder.use Octokit::Middleware::FollowRedirects
  builder.use Octokit::Response::RaiseError
  builder.use Octokit::Response::FeedParser
  builder.use RewriteRateLimitHeaders
  builder.adapter Faraday.default_adapter
end
Octokit.middleware = stack

client = Octokit::Client.new access_token: ENV['GITHUB_TOKEN'], auto_paginate: true

# Using list endpoints instead of search endpoints, because search endpoints:
# 1. Have more restrictive rate limits
# 2. Will only return up to 1,000 results

CSV.open "data.csv", "wb" do |csv|
  csv << ["repo", "library", "opened_at", "closed_at", "is_security"]
  puts "Fetching repository list..."
  repos = client.org_repos("alphagov").reject(&:archived?).filter { |r| r.topics.include? "govuk" }
  repos.each.with_index(1) do |repo, i|
    puts "Downloading: #{repo.full_name} #{i}/#{repos.count}"
    client.pull_requests(repo.full_name, state: :closed).filter { |p| p.user.login.include?("dependabot") && p.merged_at? }.each do |pull|
      is_security = pull.labels.map(&:name).include? "security"
      if library = extract_library_name(pull.title)
        csv << [repo.full_name, library, pull.created_at.iso8601, pull.closed_at.iso8601, is_security]
      end
    end
  end
end

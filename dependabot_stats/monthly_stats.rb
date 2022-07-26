require "active_support/all"
require "csv"
require "json"
require "open-uri"

def fetch_govuk_repos
  JSON.load(URI.open("https://docs.publishing.service.gov.uk/repos.json"))
end

PullRequest = Struct.new(:repo, :library, :opened_at, :closed_at)

INTERNAL_LIBRARIES = fetch_govuk_repos.map { |repo| repo["app_name"] }
FRAMEWORK_LIBRARIES = ['factory_bot_rails', 'jasmine', 'rails', 'rspec-rails', 'sass-rails']

pulls = CSV.parse(File.read("data.csv"), headers: true).map do |row|
  PullRequest.new(
    row["repo"],
    row["library"],
    Time.iso8601(row["opened_at"]),
    Time.iso8601(row["closed_at"]),
  )
end

CSV.open "monthly_stats.csv", "wb" do |out|
  out << ["Month beginning", "Total no. of pulls", "No. framework pulls", "No. internal pulls", "No. other pulls"]
  pulls.group_by { |pull| pull.opened_at.to_date.beginning_of_month }.each do |month_beginning, pulls_in_month|
    total_pulls = pulls_in_month.count
    framework_pulls = pulls_in_month.count { |pull| FRAMEWORK_LIBRARIES.include? pull.library }
    internal_pulls = pulls_in_month.count { |pull| INTERNAL_LIBRARIES.include? pull.library }
    out << [
      month_beginning,
      total_pulls,
      framework_pulls,
      internal_pulls,
      total_pulls - framework_pulls - internal_pulls
    ]
  end
end

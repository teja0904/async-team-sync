# Async Team Sync

Pulls standup-style messages from Slack, categorizes them (progress / blocker / decision / request), and generates a weekly digest. Uses OpenAI for categorization if you have a key, otherwise falls back to keyword matching. Can publish to Notion.

Also has an analytics mode — participation rates, response gap analysis, who initiates vs who responds, volume over time.

## Running it

```bash
pip install -r requirements.txt

python main.py digest             # weekly digest (demo mode)
python main.py analytics          # team activity analytics
python main.py digest --live      # from real Slack + OpenAI + Notion
```

Runs in demo mode by default with sample data from a 9-person team across 3 channels.

## Commands

**digest** — categorizes messages, builds digest with highlights, decisions, unresolved blockers, and action items. Outputs markdown and JSON.

**analytics** — messages per person, per channel, per day, busiest hours, participation rate per channel, response gap times, starter-vs-responder ratios.

## Config

Set in `.env`, all optional for demo mode:

- `SLACK_BOT_TOKEN`
- `OPENAI_API_KEY`
- `NOTION_TOKEN` + `NOTION_DATABASE_ID`

## Structure

```
main.py                  # CLI entry point
config.py                # env vars and defaults
models.py                # dataclasses
slack_collector.py       # Slack API + sample data loader
ai_summarizer.py         # OpenAI categorization + keyword fallback
digest_generator.py      # digest builder, markdown renderer
notion_writer.py         # Notion API + local JSON fallback
analytics.py             # participation, response patterns, activity metrics
sample_data/
  slack_messages.json    # 5 days, 3 channels, 55 messages
  team_members.json      # 9 people, 4 timezones
```

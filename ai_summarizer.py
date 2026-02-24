import re
from datetime import datetime
from collections import defaultdict

from models import Message, UpdateCategory, ChannelSummary


BLOCKER_KEYWORDS = [
    "blocked", "blocking", "waiting on", "waiting for", "stuck",
    "can't proceed", "dependency", "need.*approval", "need.*access",
]
DECISION_KEYWORDS = [
    "decision:", "decided", "going with", "we'll use", "we're going",
    "approved", "finalized", "standardizing", "cancelling.*in favor",
]
REQUEST_KEYWORDS = [
    "need someone", "can we", "would love eyes", "requesting",
    "need input", "need.*review", "feedback", "help with",
]


def _categorize_message(msg: Message) -> str:
    text_lower = msg.text.lower()
    for pattern in BLOCKER_KEYWORDS:
        if re.search(pattern, text_lower):
            return "blocker"
    for pattern in DECISION_KEYWORDS:
        if re.search(pattern, text_lower):
            return "decision"
    for pattern in REQUEST_KEYWORDS:
        if re.search(pattern, text_lower):
            return "request"
    return "progress"


def _summarize_text(text: str) -> str:
    text = re.sub(r"@\w+", "", text).strip()
    if ". " in text:
        text = text.split(". ")[0] + "."
    if len(text) > 150:
        text = text[:147] + "..."
    return text


def _build_channel_summary(channel: str, msgs: list[Message],
                           categorize_fn, summarize_fn) -> ChannelSummary:
    dates = [m.timestamp for m in msgs]
    date_range = f"{min(dates).strftime('%b %d')} – {max(dates).strftime('%b %d, %Y')}"
    active_members = list(set(m.user for m in msgs))

    buckets = {"progress": [], "blocker": [], "decision": [], "request": []}
    for msg in msgs:
        cat = categorize_fn(msg)
        update = UpdateCategory(
            category=cat,
            summary=summarize_fn(msg.text),
            author=msg.user,
            channel=channel,
            timestamp=msg.timestamp,
        )
        buckets[cat].append(update)

    return ChannelSummary(
        channel=channel,
        date_range=date_range,
        total_messages=len(msgs),
        active_members=active_members,
        progress_updates=buckets["progress"],
        blockers=buckets["blocker"],
        decisions=buckets["decision"],
        requests=buckets["request"],
    )


def summarize_with_templates(messages: list[Message]) -> list[ChannelSummary]:
    by_channel: dict[str, list[Message]] = defaultdict(list)
    for msg in messages:
        by_channel[msg.channel].append(msg)

    return [
        _build_channel_summary(ch, msgs, _categorize_message, _summarize_text)
        for ch, msgs in by_channel.items()
    ]


def summarize_with_ai(messages: list[Message], api_key: str,
                       model: str = "gpt-4o-mini") -> list[ChannelSummary]:
    from openai import OpenAI
    import json

    client = OpenAI(api_key=api_key)

    by_channel: dict[str, list[Message]] = defaultdict(list)
    for msg in messages:
        by_channel[msg.channel].append(msg)

    summaries = []
    for channel, channel_msgs in by_channel.items():
        dates = [m.timestamp for m in channel_msgs]
        date_range = f"{min(dates).strftime('%b %d')} – {max(dates).strftime('%b %d, %Y')}"
        active_members = list(set(m.user for m in channel_msgs))

        formatted = "\n".join(
            f"[{m.timestamp.strftime('%b %d %H:%M')}] {m.user}: {m.text}"
            for m in channel_msgs
        )

        prompt = f"""Categorize these team messages into: progress, blocker, decision, request.
For each, give a one-line summary.

Return JSON array: [{{"category": "...", "summary": "...", "author": "..."}}]

Messages:
{formatted}"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Categorize and summarize team updates. Be concise."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response.choices[0].message.content)
            items = result if isinstance(result, list) else result.get("updates", result.get("messages", []))
        except (json.JSONDecodeError, KeyError):
            items = [
                {"category": _categorize_message(m), "summary": _summarize_text(m.text), "author": m.user}
                for m in channel_msgs
            ]

        buckets = {"progress": [], "blocker": [], "decision": [], "request": []}
        for i, item in enumerate(items):
            ts = channel_msgs[i].timestamp if i < len(channel_msgs) else datetime.now()
            cat = item.get("category", "progress")
            if cat not in buckets:
                cat = "progress"
            buckets[cat].append(UpdateCategory(
                category=cat, summary=item["summary"],
                author=item["author"], channel=channel, timestamp=ts,
            ))

        summaries.append(ChannelSummary(
            channel=channel, date_range=date_range,
            total_messages=len(channel_msgs), active_members=active_members,
            progress_updates=buckets["progress"], blockers=buckets["blocker"],
            decisions=buckets["decision"], requests=buckets["request"],
        ))

    return summaries


def summarize_messages(messages: list[Message], api_key: str = "",
                       model: str = "gpt-4o-mini") -> list[ChannelSummary]:
    if api_key:
        return summarize_with_ai(messages, api_key, model)
    return summarize_with_templates(messages)

from collections import defaultdict, Counter
from datetime import datetime

from models import Message, TeamMember


def messages_per_person(messages: list[Message]) -> dict[str, int]:
    counts = Counter(m.user for m in messages)
    return dict(counts.most_common())


def messages_per_channel(messages: list[Message]) -> dict[str, int]:
    counts = Counter(m.channel for m in messages)
    return dict(counts.most_common())


def messages_per_day(messages: list[Message]) -> dict[str, int]:
    counts = Counter(m.timestamp.strftime("%Y-%m-%d") for m in messages)
    return dict(sorted(counts.items()))


def messages_per_hour(messages: list[Message]) -> dict[int, int]:
    counts = Counter(m.timestamp.hour for m in messages)
    return dict(sorted(counts.items()))


def participation_rate(messages: list[Message], team_members: list[TeamMember]) -> dict:
    active_by_channel: dict[str, set] = defaultdict(set)
    for m in messages:
        active_by_channel[m.channel].add(m.user)

    member_channels: dict[str, set] = defaultdict(set)
    for member in team_members:
        for ch in member.channels:
            member_channels[ch].add(member.name)

    result = {}
    for channel, expected in member_channels.items():
        active = active_by_channel.get(channel, set())
        total = len(expected)
        participating = len(active & expected)
        silent = expected - active
        result[channel] = {
            "total_members": total,
            "participating": participating,
            "rate": round(participating / total * 100, 1) if total else 0,
            "silent_members": sorted(silent),
        }

    return result


def response_patterns(messages: list[Message]) -> dict[str, dict]:
    by_channel: dict[str, list[Message]] = defaultdict(list)
    for m in messages:
        by_channel[m.channel].append(m)

    result = {}
    for channel, msgs in by_channel.items():
        msgs_sorted = sorted(msgs, key=lambda m: m.timestamp)
        gaps = []
        for i in range(1, len(msgs_sorted)):
            gap_minutes = (msgs_sorted[i].timestamp - msgs_sorted[i-1].timestamp).total_seconds() / 60
            if gap_minutes < 480:
                gaps.append(gap_minutes)

        if gaps:
            result[channel] = {
                "avg_gap_minutes": round(sum(gaps) / len(gaps), 1),
                "median_gap_minutes": round(sorted(gaps)[len(gaps) // 2], 1),
                "min_gap_minutes": round(min(gaps), 1),
                "max_gap_minutes": round(max(gaps), 1),
                "total_exchanges": len(gaps),
            }

    return result


def daily_activity_by_person(messages: list[Message]) -> dict[str, dict[str, int]]:
    activity: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for m in messages:
        day = m.timestamp.strftime("%Y-%m-%d")
        activity[m.user][day] += 1
    return {user: dict(days) for user, days in activity.items()}


def thread_starters_vs_responders(messages: list[Message]) -> dict[str, dict]:
    by_channel_day: dict[tuple, list[Message]] = defaultdict(list)
    for m in messages:
        key = (m.channel, m.timestamp.strftime("%Y-%m-%d"))
        by_channel_day[key].append(m)

    starters = Counter()
    responders = Counter()

    for key, msgs in by_channel_day.items():
        msgs_sorted = sorted(msgs, key=lambda m: m.timestamp)
        if msgs_sorted:
            starters[msgs_sorted[0].user] += 1
            for msg in msgs_sorted[1:]:
                responders[msg.user] += 1

    all_users = set(starters.keys()) | set(responders.keys())
    result = {}
    for user in all_users:
        s = starters.get(user, 0)
        r = responders.get(user, 0)
        total = s + r
        result[user] = {
            "started": s,
            "responded": r,
            "total": total,
            "starter_ratio": round(s / total * 100, 1) if total else 0,
        }

    return result


def generate_analytics_report(messages: list[Message],
                               team_members: list[TeamMember]) -> dict:
    return {
        "message_count": len(messages),
        "unique_contributors": len(set(m.user for m in messages)),
        "channels_active": len(set(m.channel for m in messages)),
        "date_range": {
            "start": min(m.timestamp for m in messages).strftime("%Y-%m-%d"),
            "end": max(m.timestamp for m in messages).strftime("%Y-%m-%d"),
        },
        "per_person": messages_per_person(messages),
        "per_channel": messages_per_channel(messages),
        "per_day": messages_per_day(messages),
        "per_hour": messages_per_hour(messages),
        "participation": participation_rate(messages, team_members),
        "response_patterns": response_patterns(messages),
        "daily_activity": daily_activity_by_person(messages),
        "starter_vs_responder": thread_starters_vs_responders(messages),
    }


def render_analytics_markdown(report: dict) -> str:
    lines = []
    lines.append("# Team Activity Report")
    lines.append(f"*{report['date_range']['start']} to {report['date_range']['end']}*")
    lines.append("")

    lines.append("## Overview")
    lines.append(f"- {report['message_count']} messages from {report['unique_contributors']} people across {report['channels_active']} channels")
    lines.append("")

    lines.append("## Messages per Person")
    lines.append("| Person | Messages |")
    lines.append("|--------|----------|")
    for person, count in report["per_person"].items():
        lines.append(f"| {person} | {count} |")
    lines.append("")

    lines.append("## Messages per Channel")
    lines.append("| Channel | Messages |")
    lines.append("|---------|----------|")
    for channel, count in report["per_channel"].items():
        lines.append(f"| {channel} | {count} |")
    lines.append("")

    lines.append("## Daily Volume")
    lines.append("| Date | Messages |")
    lines.append("|------|----------|")
    for date, count in report["per_day"].items():
        lines.append(f"| {date} | {count} |")
    lines.append("")

    lines.append("## Busiest Hours (UTC)")
    lines.append("| Hour | Messages |")
    lines.append("|------|----------|")
    for hour, count in sorted(report["per_hour"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| {hour:02d}:00 | {count} |")
    lines.append("")

    lines.append("## Participation Rate")
    for channel, data in report["participation"].items():
        lines.append(f"### {channel}")
        lines.append(f"- {data['participating']}/{data['total_members']} members active ({data['rate']}%)")
        if data["silent_members"]:
            lines.append(f"- Silent: {', '.join(data['silent_members'])}")
        lines.append("")

    lines.append("## Response Patterns")
    lines.append("| Channel | Avg Gap (min) | Median Gap (min) | Exchanges |")
    lines.append("|---------|---------------|------------------|-----------|")
    for channel, data in report["response_patterns"].items():
        lines.append(f"| {channel} | {data['avg_gap_minutes']} | {data['median_gap_minutes']} | {data['total_exchanges']} |")
    lines.append("")

    lines.append("## Starters vs Responders")
    lines.append("| Person | Started | Responded | Total | Starter % |")
    lines.append("|--------|---------|-----------|-------|-----------|")
    for person, data in sorted(report["starter_vs_responder"].items(),
                                key=lambda x: x[1]["total"], reverse=True):
        lines.append(f"| {person} | {data['started']} | {data['responded']} | {data['total']} | {data['starter_ratio']}% |")

    return "\n".join(lines)

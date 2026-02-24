from datetime import datetime
from pathlib import Path

from models import ChannelSummary, WeeklyDigest


HIGHLIGHT_KEYWORDS = [
    "shipped", "complete", "merged", "live", "production",
    "launched", "finished", "resolved", "reduction", "improvement",
]


def build_digest(channel_summaries: list[ChannelSummary], week_label: str) -> WeeklyDigest:
    highlights = []
    key_decisions = []
    open_blockers = []
    action_items = []

    for cs in channel_summaries:
        for update in cs.progress_updates:
            if any(kw in update.summary.lower() for kw in HIGHLIGHT_KEYWORDS):
                highlights.append(f"[{cs.channel}] {update.author}: {update.summary}")

        for decision in cs.decisions:
            key_decisions.append(f"[{cs.channel}] {decision.author}: {decision.summary}")

        for blocker in cs.blockers:
            resolved = any(
                p.author == blocker.author and p.timestamp > blocker.timestamp
                for p in cs.progress_updates
            )
            if resolved:
                highlights.append(f"Unblocked: {blocker.author} — {blocker.summary}")
            else:
                open_blockers.append(f"[{cs.channel}] {blocker.author}: {blocker.summary}")

        for req in cs.requests:
            action_items.append(f"[{cs.channel}] {req.author}: {req.summary}")

    return WeeklyDigest(
        week_of=week_label,
        generated_at=datetime.now(),
        channel_summaries=channel_summaries,
        highlights=highlights,
        open_blockers=open_blockers,
        key_decisions=key_decisions,
        action_items=action_items,
    )


def render_markdown(digest: WeeklyDigest) -> str:
    lines = []
    lines.append(f"# Weekly Digest — {digest.week_of}")
    lines.append(f"*Generated {digest.generated_at.strftime('%B %d, %Y at %I:%M %p')}*")
    lines.append("")

    total_messages = sum(cs.total_messages for cs in digest.channel_summaries)
    all_members = set()
    for cs in digest.channel_summaries:
        all_members.update(cs.active_members)
    total_decisions = sum(len(cs.decisions) for cs in digest.channel_summaries)
    total_blockers = sum(len(cs.blockers) for cs in digest.channel_summaries)

    lines.append("## At a Glance")
    lines.append(f"- **{total_messages}** messages across **{len(digest.channel_summaries)}** channels")
    lines.append(f"- **{len(all_members)}** active team members")
    lines.append(f"- **{total_decisions}** decisions made")
    lines.append(f"- **{total_blockers}** blockers surfaced ({total_blockers - len(digest.open_blockers)} resolved)")
    lines.append("")

    for section_title, items in [
        ("Highlights", digest.highlights),
        ("Key Decisions", digest.key_decisions),
        ("Open Blockers", digest.open_blockers),
    ]:
        if items:
            lines.append(f"## {section_title}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    if digest.action_items:
        lines.append("## Action Items")
        for a in digest.action_items:
            lines.append(f"- [ ] {a}")
        lines.append("")

    lines.append("---")
    lines.append("## Channel Breakdowns")
    lines.append("")

    for cs in digest.channel_summaries:
        lines.append(f"### {cs.channel}")
        lines.append(f"*{cs.date_range} · {cs.total_messages} messages · {len(cs.active_members)} contributors*")
        lines.append("")

        for label, updates in [
            ("Progress", cs.progress_updates),
            ("Blockers", cs.blockers),
            ("Decisions", cs.decisions),
            ("Open Requests", cs.requests),
        ]:
            if updates:
                lines.append(f"**{label}:**")
                for u in updates:
                    lines.append(f"- **{u.author}**: {u.summary}")
                lines.append("")

    return "\n".join(lines)


def save_markdown(content: str, output_dir: Path, week_label: str) -> Path:
    filename = f"digest_{week_label.replace(' ', '_')}.md"
    filepath = output_dir / filename
    with open(filepath, "w") as f:
        f.write(content)
    return filepath

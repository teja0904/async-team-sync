import json
from pathlib import Path

from models import WeeklyDigest


def write_to_notion(digest: WeeklyDigest, token: str, database_id: str) -> str:
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    children = []

    children.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"Weekly Digest — {digest.week_of}"}}]},
    })

    sections = [
        ("Highlights", digest.highlights, "bulleted_list_item"),
        ("Key Decisions", digest.key_decisions, "bulleted_list_item"),
        ("Open Blockers", digest.open_blockers, "bulleted_list_item"),
        ("Action Items", digest.action_items, "to_do"),
    ]

    for title, items, block_type in sections:
        if not items:
            continue
        children.append({
            "object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": title}}]},
        })
        for item in items:
            block = {"object": "block", "type": block_type}
            content = {"rich_text": [{"type": "text", "text": {"content": item}}]}
            if block_type == "to_do":
                content["checked"] = False
            block[block_type] = content
            children.append(block)

    page_data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {"title": [{"text": {"content": f"Weekly Digest — {digest.week_of}"}}]},
        },
        "children": children[:100],
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=page_data)
    response.raise_for_status()
    page_id = response.json()["id"]
    return f"https://notion.so/{page_id.replace('-', '')}"


def write_to_local(digest: WeeklyDigest, output_dir: Path) -> Path:
    output = {
        "title": f"Weekly Digest — {digest.week_of}",
        "generated_at": digest.generated_at.isoformat(),
        "highlights": digest.highlights,
        "key_decisions": digest.key_decisions,
        "open_blockers": digest.open_blockers,
        "action_items": digest.action_items,
        "channels": [
            {
                "channel": cs.channel,
                "date_range": cs.date_range,
                "total_messages": cs.total_messages,
                "active_members": cs.active_members,
                "progress": [{"author": u.author, "summary": u.summary} for u in cs.progress_updates],
                "blockers": [{"author": u.author, "summary": u.summary} for u in cs.blockers],
                "decisions": [{"author": u.author, "summary": u.summary} for u in cs.decisions],
                "requests": [{"author": u.author, "summary": u.summary} for u in cs.requests],
            }
            for cs in digest.channel_summaries
        ],
    }

    filepath = output_dir / f"digest_{digest.week_of.replace(' ', '_')}.json"
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    return filepath


def publish_digest(digest: WeeklyDigest, output_dir: Path,
                   token: str = "", database_id: str = "") -> str:
    if token and database_id:
        url = write_to_notion(digest, token, database_id)
        print(f"  Published to Notion: {url}")
        return url
    filepath = write_to_local(digest, output_dir)
    print(f"  Saved: {filepath}")
    return str(filepath)

import json
from datetime import datetime
from pathlib import Path

from models import Message, TeamMember


def load_sample_messages(sample_dir: Path) -> list[Message]:
    with open(sample_dir / "slack_messages.json") as f:
        data = json.load(f)

    messages = []
    for channel_data in data:
        channel = channel_data["channel"]
        for msg in channel_data["messages"]:
            messages.append(Message.from_dict(msg, channel))

    return sorted(messages, key=lambda m: m.timestamp)


def load_team_members(sample_dir: Path) -> list[TeamMember]:
    with open(sample_dir / "team_members.json") as f:
        data = json.load(f)
    return [TeamMember.from_dict(m) for m in data]


def collect_messages_live(token: str, channels: list[str], days_back: int = 5) -> list[Message]:
    from slack_sdk import WebClient

    client = WebClient(token=token)
    cutoff = datetime.now().timestamp() - (days_back * 86400)

    messages = []
    channels_response = client.conversations_list(types="public_channel")
    channel_map = {c["name"]: c["id"] for c in channels_response["channels"]}

    for channel_name in channels:
        clean_name = channel_name.lstrip("#")
        channel_id = channel_map.get(clean_name)
        if not channel_id:
            print(f"  channel {channel_name} not found, skipping")
            continue

        result = client.conversations_history(
            channel=channel_id, oldest=str(cutoff), limit=200,
        )

        for msg in result.get("messages", []):
            if msg.get("subtype"):
                continue
            user_info = client.users_info(user=msg["user"])
            messages.append(Message(
                user=user_info["user"]["real_name"],
                text=msg["text"],
                timestamp=datetime.fromtimestamp(float(msg["ts"])),
                channel=channel_name,
            ))

    return sorted(messages, key=lambda m: m.timestamp)


def collect_messages(mode: str, sample_dir: Path, token: str = "",
                     channels: list[str] = None, days_back: int = 5) -> list[Message]:
    if mode == "live" and token:
        return collect_messages_live(token, channels or [], days_back)
    return load_sample_messages(sample_dir)

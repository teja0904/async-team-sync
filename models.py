from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    user: str
    text: str
    timestamp: datetime
    channel: str

    @classmethod
    def from_dict(cls, data: dict, channel: str) -> "Message":
        return cls(
            user=data["user"],
            text=data["text"],
            timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
            channel=channel,
        )


@dataclass
class TeamMember:
    name: str
    role: str
    team: str
    timezone: str
    channels: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "TeamMember":
        return cls(**data)


@dataclass
class UpdateCategory:
    category: str
    summary: str
    author: str
    channel: str
    timestamp: datetime


@dataclass
class ChannelSummary:
    channel: str
    date_range: str
    total_messages: int
    active_members: list[str]
    progress_updates: list[UpdateCategory] = field(default_factory=list)
    blockers: list[UpdateCategory] = field(default_factory=list)
    decisions: list[UpdateCategory] = field(default_factory=list)
    requests: list[UpdateCategory] = field(default_factory=list)


@dataclass
class WeeklyDigest:
    week_of: str
    generated_at: datetime
    channel_summaries: list[ChannelSummary]
    highlights: list[str] = field(default_factory=list)
    open_blockers: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)

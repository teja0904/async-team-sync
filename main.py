import argparse
import json

from rich.console import Console
from rich.table import Table
from rich import box

import config
from slack_collector import collect_messages, load_team_members
from ai_summarizer import summarize_messages
from digest_generator import build_digest, render_markdown, save_markdown
from notion_writer import publish_digest
from analytics import generate_analytics_report, render_analytics_markdown

console = Console()


def show_channel_table(channel_summaries):
    table = Table(title="Channel Activity", box=box.ROUNDED, show_lines=True)
    table.add_column("Channel", style="cyan bold")
    table.add_column("Msgs", justify="center")
    table.add_column("People", justify="center")
    table.add_column("Progress", justify="center", style="green")
    table.add_column("Blockers", justify="center", style="red")
    table.add_column("Decisions", justify="center", style="yellow")
    table.add_column("Requests", justify="center", style="blue")

    for cs in channel_summaries:
        table.add_row(
            cs.channel, str(cs.total_messages), str(len(cs.active_members)),
            str(len(cs.progress_updates)), str(len(cs.blockers)),
            str(len(cs.decisions)), str(len(cs.requests)),
        )
    console.print()
    console.print(table)


def show_analytics_table(report):
    table = Table(title="Messages per Person", box=box.SIMPLE)
    table.add_column("Person")
    table.add_column("Messages", justify="right")
    table.add_column("Started", justify="right")
    table.add_column("Responded", justify="right")
    table.add_column("Starter %", justify="right")

    sr = report.get("starter_vs_responder", {})
    for person, count in report["per_person"].items():
        sr_data = sr.get(person, {})
        table.add_row(
            person, str(count),
            str(sr_data.get("started", "-")),
            str(sr_data.get("responded", "-")),
            f"{sr_data.get('starter_ratio', 0)}%",
        )
    console.print()
    console.print(table)

    console.print()
    table = Table(title="Participation Rate", box=box.SIMPLE)
    table.add_column("Channel")
    table.add_column("Active / Total", justify="center")
    table.add_column("Rate", justify="right")
    table.add_column("Silent", style="dim")

    for channel, data in report["participation"].items():
        silent = ", ".join(data["silent_members"]) if data["silent_members"] else "-"
        table.add_row(
            channel,
            f"{data['participating']}/{data['total_members']}",
            f"{data['rate']}%",
            silent,
        )
    console.print(table)

    rp = report.get("response_patterns", {})
    if rp:
        console.print()
        table = Table(title="Response Patterns", box=box.SIMPLE)
        table.add_column("Channel")
        table.add_column("Avg Gap", justify="right")
        table.add_column("Median Gap", justify="right")
        table.add_column("Exchanges", justify="right")

        for channel, data in rp.items():
            table.add_row(
                channel,
                f"{data['avg_gap_minutes']}m",
                f"{data['median_gap_minutes']}m",
                str(data["total_exchanges"]),
            )
        console.print(table)


def get_messages(args):
    mode = "live" if args.live else "demo"
    messages = collect_messages(
        mode=mode, sample_dir=config.SAMPLE_DATA_DIR,
        token=config.SLACK_BOT_TOKEN, channels=config.SLACK_CHANNELS,
        days_back=config.DIGEST_LOOKBACK_DAYS,
    )
    team_members = load_team_members(config.SAMPLE_DATA_DIR)
    console.print(f"  {len(messages)} messages, {len(team_members)} team members")
    return messages, team_members


def cmd_digest(args):
    console.print(f"\n[bold]async-team-sync[/bold] digest  mode={'live' if args.live else 'demo'}\n")
    messages, team_members = get_messages(args)

    api_key = config.OPENAI_API_KEY if args.live else ""
    channel_summaries = summarize_messages(messages, api_key=api_key, model=config.OPENAI_MODEL)
    show_channel_table(channel_summaries)

    week_label = "Week of Feb 17, 2025"
    digest = build_digest(channel_summaries, week_label)

    if digest.highlights:
        console.print(f"\n[bold]Highlights[/bold] ({len(digest.highlights)})")
        for h in digest.highlights[:5]:
            console.print(f"  {h}")
    if digest.key_decisions:
        console.print(f"\n[bold]Decisions[/bold] ({len(digest.key_decisions)})")
        for d in digest.key_decisions[:5]:
            console.print(f"  {d}")

    md_content = render_markdown(digest)
    md_path = save_markdown(md_content, config.OUTPUT_DIR, week_label)
    console.print(f"\n  markdown: {md_path}")

    publish_digest(
        digest, output_dir=config.OUTPUT_DIR,
        token=config.NOTION_TOKEN if args.live else "",
        database_id=config.NOTION_DATABASE_ID if args.live else "",
    )

    console.print("\n[green]Done.[/green]\n")


def cmd_analytics(args):
    console.print(f"\n[bold]async-team-sync[/bold] analytics  mode={'live' if args.live else 'demo'}\n")
    messages, team_members = get_messages(args)

    report = generate_analytics_report(messages, team_members)
    show_analytics_table(report)

    md = render_analytics_markdown(report)
    md_path = config.OUTPUT_DIR / "activity_report.md"
    with open(md_path, "w") as f:
        f.write(md)
    console.print(f"\n  Saved: {md_path}")

    json_path = config.OUTPUT_DIR / "activity_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    console.print(f"  Saved: {json_path}")

    console.print("\n[green]Done.[/green]\n")


def main():
    parser = argparse.ArgumentParser(description="Async Team Sync")
    sub = parser.add_subparsers(dest="command")

    digest_parser = sub.add_parser("digest", help="Generate weekly digest")
    digest_parser.add_argument("--live", action="store_true", help="Use live APIs")

    analytics_parser = sub.add_parser("analytics", help="Team activity analytics")
    analytics_parser.add_argument("--live", action="store_true", help="Use live APIs")

    args = parser.parse_args()

    if args.command == "digest":
        cmd_digest(args)
    elif args.command == "analytics":
        cmd_analytics(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

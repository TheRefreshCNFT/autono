"""Autono CLI — command center for the 13 autonomous agents.

Usage:
    autono launch          Launch all 13 agents
    autono status          Get status of all agents
    autono ask <agent> <q> Ask an agent a question
    autono chain           Show sidechain status
    autono agents          List all agents and their roles
"""

from __future__ import annotations

import asyncio
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def main() -> None:
    """Autono — 13 Autonomous Agents powering a Cardano Sidechain."""
    pass


@main.command()
def launch() -> None:
    """Launch all 13 agents.  They run autonomously from here."""
    from autono.services.orchestrator import Orchestrator

    console.print(Panel.fit(
        "[bold cyan]AUTONO SIDECHAIN[/bold cyan]\n"
        "[dim]13 Autonomous Agents — Faster, Cheaper, Modern Cardano[/dim]\n\n"
        "Core Mission: Make interacting with Cardano faster, cheaper,\n"
        "more user-friendly, and modern.\n\n"
        "Agents have full autonomy. They answer to you when you reach out.\n"
        "Anything legal goes in pursuit of the mission.",
        title="Launching",
        border_style="cyan",
    ))

    orchestrator = Orchestrator()

    # Display agent roster
    _show_agents_table(orchestrator)

    console.print("\n[bold green]All 13 agents launching...[/bold green]\n")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        asyncio.run(orchestrator.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down agents...[/yellow]")
        sys.exit(0)


@main.command()
def agents() -> None:
    """List all 13 agents and their roles."""
    from autono.services.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    _show_agents_table(orchestrator)


@main.command()
def status() -> None:
    """Get current status of all agents."""
    from autono.services.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    reports = orchestrator.status()

    table = Table(title="Agent Status Reports", border_style="cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Agent", style="bold cyan")
    table.add_column("Status", style="green")
    table.add_column("Inbox", justify="right")
    table.add_column("Capabilities", style="dim")

    for i, report in enumerate(reports, 1):
        caps = ", ".join(report["capabilities"][:3])
        if len(report["capabilities"]) > 3:
            caps += f" +{len(report['capabilities']) - 3}"
        table.add_row(
            str(i), report["agent"], report["status"],
            str(report["inbox_size"]), caps,
        )

    console.print(table)


@main.command()
@click.argument("agent_name")
@click.argument("question")
def ask(agent_name: str, question: str) -> None:
    """Ask an agent a question — they must answer."""
    from autono.services.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    answer = orchestrator.ask(agent_name, question)
    console.print(Panel(answer, title=f"Response from {agent_name}", border_style="cyan"))


@main.command()
def chain() -> None:
    """Show sidechain infrastructure status."""
    from autono.services.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    info = orchestrator.chain_status()

    console.print(Panel.fit(
        f"[bold]Consensus:[/bold] {info['consensus']}\n\n"
        f"[bold]Blockchain:[/bold] {info['blockchain']}\n\n"
        f"[bold]Bridge:[/bold] {info['bridge']}\n\n"
        f"[bold]State:[/bold] {info['state']}",
        title="Sidechain Status",
        border_style="cyan",
    ))


def _show_agents_table(orchestrator) -> None:
    table = Table(title="The 13 Autonomous Agents", border_style="cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Agent", style="bold cyan", width=20)
    table.add_column("Role", style="white")
    table.add_column("Capabilities", style="dim")

    for i, (name, agent) in enumerate(orchestrator.agents.items(), 1):
        caps = ", ".join(c.value for c in agent.capabilities[:3])
        if len(agent.capabilities) > 3:
            caps += f" +{len(agent.capabilities) - 3}"
        table.add_row(str(i), name, agent.role, caps)

    console.print(table)


if __name__ == "__main__":
    main()

"""Tests for the 13 autonomous agents."""

from __future__ import annotations

import asyncio

import pytest

from autono.agents import ALL_AGENTS
from autono.core.agent_base import AgentStatus, Message
from autono.core.message_bus import MessageBus
from autono.services.orchestrator import Orchestrator


def test_all_13_agents_exist():
    assert len(ALL_AGENTS) == 13


def test_each_agent_instantiates():
    for agent_cls in ALL_AGENTS:
        agent = agent_cls()
        assert agent.name
        assert agent.role
        assert len(agent.capabilities) > 0
        assert agent.status == AgentStatus.IDLE


def test_orchestrator_creates_all_agents():
    orch = Orchestrator()
    assert len(orch.agents) == 25


def test_agent_names_are_unique():
    names = set()
    for agent_cls in ALL_AGENTS:
        agent = agent_cls()
        assert agent.name not in names, f"Duplicate agent name: {agent.name}"
        names.add(agent.name)


def test_agent_report():
    for agent_cls in ALL_AGENTS:
        agent = agent_cls()
        report = agent.report()
        assert "agent" in report
        assert "role" in report
        assert "status" in report
        assert "capabilities" in report


def test_agent_answer():
    for agent_cls in ALL_AGENTS:
        agent = agent_cls()
        answer = agent.answer("What is your status?")
        assert agent.name in answer
        assert isinstance(answer, str)


def test_message_bus_registration():
    bus = MessageBus()
    for agent_cls in ALL_AGENTS:
        agent = agent_cls()
        bus.register(agent)
    assert len(bus._agents) == 13


def test_human_council_query():
    orch = Orchestrator()
    answer = orch.ask("ChainArchitect", "How is the chain?")
    assert "ChainArchitect" in answer


def test_human_council_all_reports():
    orch = Orchestrator()
    reports = orch.status()
    assert len(reports) == 25


def test_chain_status():
    orch = Orchestrator()
    info = orch.chain_status()
    assert "consensus" in info
    assert "blockchain" in info
    assert "bridge" in info
    assert "state" in info

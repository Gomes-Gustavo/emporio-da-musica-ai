"""Offline checks of the agent wiring: no API call is made here."""

from datetime import datetime

import pytest
from google import genai
from google.genai import types

from emporio import agent

NOW = datetime(2026, 3, 22, 14, 30, tzinfo=agent.STORE_TIMEZONE)  # a Sunday


class FakeChats:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return "chat"


class FakeClient:
    def __init__(self):
        self.chats = FakeChats()


def test_prompt_carries_the_current_date_and_weekday():
    prompt = agent.build_system_prompt(NOW)
    assert "domingo, 22/03/2026, 14:30" in prompt


def test_prompt_uses_the_contacts_decided_for_the_manual_inconsistencies():
    prompt = agent.build_system_prompt(NOW)
    assert "WhatsApp (67) 3321-4500" in prompt
    assert "Telefone (67) 3341-4444" in prompt
    assert "contato@emporiodamusica.com.br" in prompt  # a domain cannot have an accent
    assert "contato@empóriodamusica" not in prompt


def test_chat_gets_the_model_tools_and_prompt(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    client = FakeClient()

    agent.make_chat(client, now=NOW)

    kwargs = client.chats.kwargs
    assert kwargs["model"] == "gemini-3.5-flash-lite"
    assert kwargs["config"].tools == agent.TOOLS
    assert "domingo, 22/03/2026" in kwargs["config"].system_instruction


def test_model_can_be_chosen_with_an_environment_variable(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "another-model")
    client = FakeClient()

    agent.make_chat(client, now=NOW)

    assert client.chats.kwargs["model"] == "another-model"


def test_gemini_accepts_every_tool_signature():
    # building the schema is what the SDK does before the first request; a bad signature would fail there
    api_client = genai.Client(api_key="not-a-real-key")._api_client
    declarations = {
        tool.__name__: types.FunctionDeclaration.from_callable(client=api_client, callable=tool)
        for tool in agent.TOOLS
    }

    assert set(declarations) == {"search_products", "get_product", "get_customer_orders", "get_policy"}
    topic = declarations["get_policy"].parameters.properties["topic"]
    assert set(topic.enum) == {
        "about", "hours", "payment", "returns", "shipping", "promotions", "warranty", "privacy"
    }
    assert declarations["get_policy"].parameters.required == ["topic"]


@pytest.mark.parametrize("tool", agent.TOOLS, ids=lambda t: t.__name__)
def test_every_tool_has_a_description_for_the_model(tool):
    assert tool.__doc__ and len(tool.__doc__.split()) > 10

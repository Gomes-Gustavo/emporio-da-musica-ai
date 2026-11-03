"""Offline checks of the agent wiring: no API call is made here."""

from datetime import datetime

import pytest
from google import genai
from google.genai import _extra_utils, types

from emporio import agent
from emporio.policies import load_policies

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


def test_prompt_hours_are_the_ones_in_the_manual():
    # the model once answered "08:00" twice with the manual in hand: the prompt carries the hours itself
    manual = " ".join(load_policies()["hours"].split())
    prompt = agent.build_system_prompt(NOW)
    for line in ("Segunda a Sexta-feira 09:00 às 18:00", "Sábado 09:00 às 13:00", "Domingo e Feriados Fechado"):
        assert line in manual  # fails if the manual changes: update STORE_HOURS
    assert agent.STORE_HOURS in prompt
    assert "segunda a sexta 09:00 às 18:00, sábado 09:00 às 13:00, domingo e feriados fechado" == agent.STORE_HOURS


def test_thinking_effort_is_off_by_default_and_chosen_with_an_environment_variable(monkeypatch):
    monkeypatch.delenv("GEMINI_THINKING_LEVEL", raising=False)
    client = FakeClient()
    agent.make_chat(client, now=NOW)
    assert client.chats.kwargs["config"].thinking_config is None

    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "low")
    agent.make_chat(client, now=NOW)
    assert client.chats.kwargs["config"].thinking_config.thinking_level == types.ThinkingLevel.LOW


def history_with(results=(), customer_says=""):
    """A chat history: the customer's message and tool results as the SDK records them."""
    contents = [types.Content(role="user", parts=[types.Part(text=customer_says)])]
    for result in results:
        part = types.Part(function_response=types.FunctionResponse(name="any_tool", response=result))
        contents.append(types.Content(role="user", parts=[part]))
    return contents


def test_prices_that_come_from_the_tool_results_are_supported():
    history = history_with([{"price": {"final_price_brl": 599.9, "pix_price_brl": 569.91}}])

    assert agent.unsupported_amounts(history, "Custa R$ 599,90 (R$ 569,91 no PIX).") == []


def test_a_price_the_tools_never_returned_is_caught():
    # the model once wrote R$ 599,00 for a product that costs R$ 599,90
    history = history_with([{"price": {"final_price_brl": 599.9}}])

    assert agent.unsupported_amounts(history, "Custa R$ 599,00.") == ["R$ 599,00"]


def test_thousands_separators_are_read_like_the_tool_numbers():
    history = history_with([{"final_price_brl": 11499.0}])

    assert agent.unsupported_amounts(history, "Sai por R$ 11.499,00.") == []


def test_amounts_from_the_policy_text_and_from_the_customer_are_supported():
    history = history_with(
        [{"section": "5. Frete", "text": "taxa fixa de R$ 35,00 abaixo de R$ 500,00"}],
        customer_says="tenho R$ 1000 para gastar",
    )

    assert agent.unsupported_amounts(history, "Frete de R$ 35,00; seu limite é R$ 1.000,00.") == []


def test_a_quantity_is_not_mistaken_for_a_price():
    # stock_quantity 5 must not make "R$ 5,00" look grounded
    history = history_with([{"stock_quantity": 5, "final_price_brl": 100.0}])

    assert agent.unsupported_amounts(history, "Custa R$ 5,00.") == ["R$ 5,00"]


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
    # a plain str: the SDK cannot run a tool whose parameter is a Literal (see the test below)
    assert declarations["get_policy"].parameters.properties["topic"].type == types.Type.STRING
    assert declarations["get_policy"].parameters.required == ["topic"]
    assert declarations["search_products"].parameters.properties["max_price"].type == types.Type.NUMBER


@pytest.mark.parametrize(
    "name, args",
    [
        ("search_products", {"query": "yamaha", "category": "Violões", "max_price": 1000.0, "in_stock_only": True}),
        ("search_products", {"max_price": 1000}),  # a whole number can arrive as an int
        ("get_product", {"name_or_id": "takamine gd20"}),
        ("get_customer_orders", {"email_or_phone": "pedro.oliveira@jmail.com", "order_id": 1}),
        ("get_policy", {"topic": "shipping"}),
    ],
)
def test_the_sdk_runs_every_tool_the_way_a_live_chat_does(name, args):
    # The SDK checks each argument against its annotation before calling the tool. A Literal annotation made
    # that check raise, so get_policy never ran and the model got an error it described as "instabilidade".
    call = types.Part(function_call=types.FunctionCall(name=name, args=args))
    response = types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[call]))]
    )
    function_map = _extra_utils.get_function_map(types.GenerateContentConfig(tools=agent.TOOLS))

    (part,) = _extra_utils.get_function_response_parts(response, function_map)

    assert "error" not in part.function_response.response, part.function_response.response


@pytest.mark.parametrize("tool", agent.TOOLS, ids=lambda t: t.__name__)
def test_every_tool_has_a_description_for_the_model(tool):
    assert tool.__doc__ and len(tool.__doc__.split()) > 10

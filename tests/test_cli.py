"""The chat loop and the tool-call trace, with a scripted fake chat: no API call is made here."""

from types import SimpleNamespace

from google import genai
from google.genai import types

from emporio import agent, cli


def model_calls(name: str, **args) -> types.Content:
    return types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))])


class FakeChat:
    """Plays a script: each item is an exception to raise or (text, tool calls the model makes first)."""

    def __init__(self, script, history=None):
        self.script = list(script)
        self.history = list(history or [])

    def get_history(self):
        return list(self.history)

    def send_message(self, message):
        step = self.script.pop(0)
        if isinstance(step, Exception):
            self.history.append(model_calls("half_done"))  # the SDK records a turn before it fails
            raise step
        text, calls = step
        self.history.extend(model_calls(name, **args) for name, args in calls)
        return SimpleNamespace(text=text)


class FakeClient:
    def __init__(self, *chats):
        self.pending = list(chats)
        self.created = []
        self.chats = self

    def create(self, **kwargs):
        self.created.append(kwargs)
        chat = self.pending.pop(0)
        chat.history = list(kwargs.get("history") or [])
        return chat


def run_loop(client, inputs):
    typed, shown = iter(inputs), []

    def read(prompt):
        try:
            return next(typed)
        except StopIteration:
            raise EOFError  # what input() raises when the input ends

    cli.chat_loop(client, read=read, write=shown.append)
    return shown


def test_reply_lists_only_the_tool_calls_of_this_turn():
    older = model_calls("get_product", name_or_id="95")
    chat = FakeChat([("Abrimos às 9h.", [("get_policy", {"topic": "hours"})])], history=[older])

    text, calls = agent.reply(chat, "Que horas abrem?")

    assert text == "Abrimos às 9h."
    assert calls == ["get_policy(topic='hours')"]


def test_reply_without_tool_calls_has_an_empty_trace():
    text, calls = agent.reply(FakeChat([("Olá!", [])]), "Oi")

    assert (text, calls) == ("Olá!", [])


def test_loop_prints_each_consultation_then_the_answer_and_stops_on_sair():
    chat = FakeChat([("Tem sim.", [("search_products", {"category": "Violões", "max_price": 1000.0})])])

    shown = run_loop(FakeClient(chat), ["Quais violões até 1000?", "", "sair"])

    assert "  [consulta] search_products(category='Violões', max_price=1000.0)" in shown
    assert shown.index("Atendente: Tem sim.") > shown.index("  [consulta] search_products(category='Violões', max_price=1000.0)")
    assert shown[-1] == "Atendente: Até logo!"
    assert chat.script == []  # the blank line was not sent to the model


def test_loop_ends_when_the_input_ends():
    shown = run_loop(FakeClient(FakeChat([])), [])

    assert shown[-1] == "Atendente: Até logo!"


def test_api_error_keeps_the_session_and_drops_the_half_finished_turn():
    failing = FakeChat([genai.errors.APIError(429, {"error": {"message": "quota"}})])
    recovered = FakeChat([("Voltei!", [])])
    client = FakeClient(failing, recovered)

    shown = run_loop(client, ["Oi", "Oi de novo", "sair"])

    assert any("erro 429" in line for line in shown)
    assert "Atendente: Voltei!" in shown
    # the new chat starts from the history before the failed turn, without the dangling function call
    assert client.created[1]["history"] == []

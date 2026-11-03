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
        text, calls, *results = step  # results: what the tools returned, as dicts
        self.history.extend(model_calls(name, **args) for name, args in calls)
        for result in results[0] if results else []:
            part = types.Part(function_response=types.FunctionResponse(name="get_product", response=result))
            self.history.append(types.Content(role="user", parts=[part]))
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


def test_reply_shows_a_tool_that_failed_in_the_trace():
    # the SDK hands a failing tool's error to the model; the trace must show it, or it is invisible
    chat = FakeChat([("Estou com instabilidade.", [("get_policy", {"topic": "hours"})], [{"error": "boom"}])])

    _, calls = agent.reply(chat, "Que horas abrem?")

    assert calls == ["get_policy(topic='hours')", "get_product FALHOU: boom"]


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


def test_network_failure_keeps_the_session_too():
    # no internet raises an httpx error, not a genai APIError: the chat must not crash and lose the history
    failing = FakeChat([ConnectionError("getaddrinfo failed")])
    recovered = FakeChat([("Voltei!", [])])

    shown = run_loop(FakeClient(failing, recovered), ["Oi", "Oi de novo", "sair"])

    assert any("Não consegui responder agora (ConnectionError)" in line for line in shown)
    assert "Atendente: Voltei!" in shown


def test_empty_answer_is_asked_again_once_from_the_same_point():
    # the model sometimes repeats one tool call until the SDK gives up and returns no text
    looping = FakeChat([("", [("get_policy", {"topic": "hours"})] * 10)])
    fine = FakeChat([("Abrimos às 9h.", [("get_policy", {"topic": "hours"})])])
    client = FakeClient(looping, fine)

    shown = run_loop(client, ["Que horas abrem?", "sair"])

    assert "Atendente: Abrimos às 9h." in shown
    assert not any("Não consegui" in line for line in shown)
    assert shown.count("  [consulta] get_policy(topic='hours')") == 1  # only the attempt that answered is shown
    assert client.created[1]["history"] == []  # the retry drops the looping attempt


def test_a_price_the_tools_never_returned_is_asked_again_once():
    # the model once wrote R$ 599,00 for a R$ 599,90 product: the customer must not see it
    tool_result = [{"final_price_brl": 599.9}]
    wrong = FakeChat([("O C40 custa R$ 599,00.", [], tool_result)])
    right = FakeChat([("O C40 custa R$ 599,90.", [], tool_result)])
    client = FakeClient(wrong, right)

    shown = run_loop(client, ["Quanto custa o C40?", "sair"])

    assert "Atendente: O C40 custa R$ 599,90." in shown
    assert not any("599,00" in line for line in shown)
    assert client.created[1]["history"] == []


def test_two_wrong_prices_give_up_instead_of_showing_one():
    tool_result = [{"final_price_brl": 599.9}]
    wrong = ("O C40 custa R$ 599,00.", [], tool_result)
    client = FakeClient(FakeChat([wrong]), FakeChat([wrong]), FakeChat([]))

    shown = run_loop(client, ["Quanto custa o C40?", "sair"])

    assert "Atendente: Não consegui formular uma resposta. Pode repetir?" in shown
    assert not any("599,00" in line for line in shown)


def test_two_empty_answers_give_up_and_keep_the_session():
    # one chat per attempt, then a fresh one that keeps the session going
    client = FakeClient(FakeChat([("", [])]), FakeChat([("", [])]), FakeChat([("Oi!", [])]))

    shown = run_loop(client, ["Que horas abrem?", "Oi", "sair"])

    assert "Atendente: Não consegui formular uma resposta. Pode repetir?" in shown
    assert "Atendente: Oi!" in shown

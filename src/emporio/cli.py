"""Command-line chat with the agent: `uv run emporio`. The history lasts only while the program runs."""

import os
import sys

from dotenv import load_dotenv
from google import genai

from emporio.agent import make_chat, reply, unsupported_amounts

EXIT_WORDS = {"sair", "exit", "quit"}


def _answer(client: genai.Client, chat, history: list, message: str):
    """The answer, its consultations and the chat to keep using.

    An empty answer (the model repeated one tool call until the SDK gave up) or one with a price the
    tools never returned is asked again once from the same point.
    """
    for _ in range(2):
        text, calls = reply(chat, message)
        if text and not unsupported_amounts(chat.get_history(), text):
            return chat, text, calls
        chat = make_chat(client, history=history)
    return chat, "", []


def chat_loop(client: genai.Client, read=input, write=print) -> None:
    chat = make_chat(client)
    write("Empório da Música - atendimento (digite 'sair' para encerrar)")
    while True:
        try:
            message = read("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.lower() in EXIT_WORDS:
            break
        if not message:
            continue

        history = chat.get_history()
        try:
            chat, text, calls = _answer(client, chat, history, message)
        except Exception as error:  # an API error, no internet...: the customer keeps the conversation
            # a turn that fails midway leaves a function call without its answer, which the API rejects
            chat = make_chat(client, history=history)
            reason = f"erro {error.code}" if hasattr(error, "code") else type(error).__name__
            write(f"Atendente: Não consegui responder agora ({reason}). Tente de novo em instantes.")
            continue

        for call in calls:
            write(f"  [consulta] {call}")
        write(f"Atendente: {text or 'Não consegui formular uma resposta. Pode repetir?'}")
    write("Atendente: Até logo!")


def main() -> None:
    load_dotenv()
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        sys.exit("Set GEMINI_API_KEY in a .env file or in the environment (see .env.example).")
    chat_loop(genai.Client())

# Empório da Música — Customer Service Agent

Python prototype of a text-message agent for the fictional music store Empório da Música (Campo Grande, MS, Brazil), for Artefact's 2026 AI Engineer technical challenge.

The agent takes on the store's voice, looks up operational data when a question needs it (products, stock, prices, orders, promotions), and applies internal policies (hours, payment, exchanges, shipping) when those rules matter.

Customer messages and the agent's replies stay in Portuguese. That is the language of the store, of its policy manual, and of the sample questions in the brief. Documentation for this project is in English.

## Tooling

Python, the virtual environment, and dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

`uv sync` creates `.venv` and installs the packages pinned in `uv.lock`. Add a library with `uv add <package>`.

## Status

Repository initialized with the store data. The agent is not implemented yet.

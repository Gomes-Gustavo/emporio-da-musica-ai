# Empório da Música — Customer Service Agent

A Python customer service agent for the fictional music store Empório da Música (Campo Grande, MS, Brazil), built for Artefact's 2026 AI Engineer technical challenge.

The agent answers in the store's voice, looks up operational data when a question needs it (products, stock, prices, promotions, orders) and applies the store's policies (hours, payment, exchanges, shipping, warranty) when those rules matter. It runs as a command-line chat and talks to Google's Gemini API.

Customer messages and the agent's replies are in Portuguese, the language of the store, of its policy manual and of the sample questions in the brief. Everything else (this documentation, code comments, commit messages) is in English.

## Contents

- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Technical decisions](#technical-decisions)
- [Data assumptions](#data-assumptions)
- [Policy manual inconsistencies](#policy-manual-inconsistencies)
- [Example conversations](#example-conversations)
- [Tests](#tests)
- [Known limitations](#known-limitations)
- [What I would do with more time](#what-i-would-do-with-more-time)
- [Use of AI assistants](#use-of-ai-assistants)

## Quick start

### Requirements

- [uv](https://docs.astral.sh/uv/), which manages Python, the virtual environment and the dependencies. Python 3.12 is pinned in `.python-version` and uv installs it if needed.
- A Gemini API key. The free tier is enough: create one in [Google AI Studio](https://aistudio.google.com/apikey).

### Setup

```bash
git clone https://github.com/Gomes-Gustavo/emporio-da-musica-ai.git
cd emporio-da-musica-ai
uv sync
```

`uv sync` creates `.venv` and installs the versions pinned in `uv.lock`. Then create your `.env` from the template and put your key in it:

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

```text
GEMINI_API_KEY=your-key-here
```

`.env` is gitignored.

### Run

```bash
uv run emporio
```

Type a customer message and press Enter; `sair` (or Ctrl+C) ends the chat. The history lasts while the program runs. Each lookup the agent makes is printed as `[consulta] ...` before its answer, so you can see what it consulted. A failure (an API error, no internet) does not end the conversation, and the question can be asked again.

Some questions to try (they are in Portuguese, like the store): `Quais violões vocês têm até R$ 1000?`, `Quanto custa o Takamine GD20? Tem promoção?`, `Que horas vocês abrem no sábado?`. For orders, the demo customers are in `data/desafio_tecnico_ai_eng - customers.csv` (for example `pedro.oliveira@jmail.com`).

### Configuration

| Variable | Required | Meaning |
| --- | --- | --- |
| `GEMINI_API_KEY` | yes | Your Gemini API key (`GOOGLE_API_KEY` is also accepted). |
| `GEMINI_MODEL` | no | The model to use. Default: `gemini-3.5-flash-lite`. |
| `GEMINI_THINKING_LEVEL` | no | How much the model reasons before answering: `minimal`, `low`, `medium` or `high`. Default: the model's own. |

The data is fictional, and on the free tier Google may use prompts and responses to improve its products, so do not type real personal data. A customer message usually costs two to four API calls (the lookups plus the final answer), which matters for the free tier's rate limits.

## How it works

```text
customer message
      │
      ▼
Gemini (system prompt + 4 tools) ◀──▶ tools (Python) ◀──▶ CSVs and policy manual
      │
      ▼
answer check ──▶ reply to the customer
```

The model decides when to call a tool, Python runs it and returns plain data, and the model writes the reply from that data.

| Tool | What it does |
| --- | --- |
| `search_products` | Searches the catalog by words, category and maximum price. Returns the cheapest matches first, each with availability, promotion, PIX price and the maximum interest-free installments. |
| `get_product` | One product in detail (specs, stock, ended promotions). If it cannot be bought, it also returns similar products that can. |
| `get_customer_orders` | The orders of a customer, who identifies themselves by e-mail or phone number: status, tracking, delivery estimate, items, total, and the day counts the return rules need. |
| `get_policy` | One section of the policy manual (about, hours, payment, returns, shipping, promotions, warranty, privacy), exactly as written. |

What keeps the answers reliable:

- **The model never does arithmetic.** Promotional and PIX prices, installments and day counts are computed in code (`Decimal`, rounded half up to the cent) and handed over ready.
- **Answers are checked.** Every `R$` amount in a reply must come from a tool result, from the policy text or from the customer's own message. A reply with an amount that was never returned, or with no text at all, is asked again once; if it fails again, the customer gets "Não consegui formular uma resposta. Pode repetir?" instead of a wrong price.
- **The agent cannot promise what it cannot do.** It has no tool to register complaints or change orders, so it gives the store's contact channels and never says it forwarded anything.

### Project layout

```text
data/              the CSVs and the policy manual (PDF) from the challenge
notebooks/         01_data_audit.ipynb: the data audit, each finding ending in a decision
src/emporio/
  data.py          CSVs into typed, immutable records
  tools.py         the four tools the agent calls
  policies.py      splits the manual PDF into its numbered sections
  agent.py         system prompt, Gemini chat and answer checks
  cli.py           the command-line chat (`uv run emporio`)
tests/             offline tests, no API calls
examples/          recorded conversations
```

## Technical decisions

- **Retrieval: function calling over structured data, no RAG.** The data is small and tabular (65 products, 50 customers, 20 orders), and the questions are exact: a price, a stock count, the status of one order. Exact filters answer them deterministically and can be tested; embeddings would add moving parts and the risk of retrieving the wrong passage, with nothing to gain. The policy manual (8 pages) is split by its ten numbered sections, and the model reads one section by topic. Section 7 (service guidelines) lives in the system prompt and section 10 (final provisions) is internal, so neither is a tool topic.
- **Framework: the plain `google-genai` SDK with automatic function calling.** This is one agent with four tools and no branching workflow. A graph or agent framework such as LangGraph would add abstraction without removing any code here. If the flows grow (multi-step returns, hand-off, approvals), that is where I would move to one.
- **LLM: `gemini-3.5-flash-lite`.** It supports function calling and fits the free tier's daily request limit (around 500 requests a day in AI Studio, which varies per account), where the larger Flash models allow only a few dozen. `GEMINI_MODEL` switches the model without code changes.
- **Prompt strategy.** The system prompt is in Portuguese and follows the manual's service guidelines (section 7): an informal but professional tone, the standard service flow, instruments only, accessories redirected politely, and no price, stock or deadline without a lookup. It adds explicit rules for what went wrong in testing: how promotions, PIX and installments combine, which date each return window counts from, status reported exactly as recorded, no invented details, and messages formatted for WhatsApp. It carries the current date and time in Campo Grande, so the agent can say whether the store is open, and the store hours themselves (a test checks them against the manual).
- **Arithmetic and dates in code, not in the model.** Language models make small mistakes with numbers; here every figure the customer sees is computed and checked by Python.
- **Standard library at runtime.** The agent reads the CSVs with `csv` and the PDF with `pypdf`; pandas is only used in the audit notebook (a development dependency).
- **Audit before coding.** The data was explored in a notebook first, and each finding ended in a decision that the code follows (see Data assumptions).
- **Tests that run the real path.** The tests use no API. They freeze the date, run every tool the way the SDK does (which caught tool signatures the SDK rejects), and cover the answer checks and the chat's failure handling with a scripted fake chat.

## Data assumptions

The CSVs in `data/` were audited in [`notebooks/01_data_audit.ipynb`](notebooks/01_data_audit.ipynb). Each finding there ends in a decision, and `src/emporio/data.py` and the agent's tools follow them:

- **The CSVs are the source of truth.** Three categories (woodwinds, brass, orchestral strings) have no products, so the agent never offers items that are not in the data.
- **A product is available only when it is `active` and has stock.** Status wins over stock.
- **Only promotions with `is_active = 1` apply.** No product has two active promotions, so there is no tie-break; some products do have two inactive ones. The 5% PIX discount does not stack on a promotional price (manual 6.2). An ended promotion is reported as ended, with the current price.
- **`total_brl` is the recorded order total.** It is never recomputed from current prices.
- **A missing tracking code means the order has not shipped yet.** Cancelled orders carry the reason in `notes`.
- **An e-mail alone does not identify a customer.** Two customer records share one, so the agent asks for the phone number when an e-mail is ambiguous.
- **The reference date is the real current date,** because a customer service agent answers on the day the customer writes. Day counts are computed in code, never by the model. Order status is reported as recorded.
- **The receipt date of an order is assumed to be `estimated_delivery`,** since the data has no actual delivery date.
- **Installments are computed in code,** not by the model. Manual 3.1 is read as "no installment under R$ 50 up to 3x, under R$ 80 from 4x to 6x, under R$ 100 from 7x to 12x", and each product carries its maximum interest-free installments at its final price.
- **Two return windows, two start dates.** The 7-day regret window counts from receipt (the estimated delivery date, see above) and the 30-day defect window counts from the purchase (manual 4.2), so orders carry both `days_since_estimated_delivery` and `days_since_order`.
- **`specs` stays a dictionary,** because its keys depend on the product category.

## Policy manual inconsistencies

- **Phone and WhatsApp.** Section 1.2 labels (67) 3341-4444 as "Telefone / WhatsApp", while section 7 names (67) 3321-4500 as the WhatsApp channel. The agent gives **(67) 3321-4500 as the WhatsApp** and **(67) 3341-4444 as the phone**.

## Example conversations

Real sessions, recorded with the command-line chat and left exactly as the agent wrote them (the lines starting with `[consulta]` show the lookups it made):

| File | What it shows |
| --- | --- |
| [`01-catalog-and-installments.md`](examples/01-catalog-and-installments.md) | A budget search, a product in detail and an installment question. |
| [`02-promotions.md`](examples/02-promotions.md) | An ended promotion, an active one, and why PIX does not stack on it. |
| [`03-return.md`](examples/03-return.md) | A return request on a real order, with both return windows expired. |
| [`04-store-info.md`](examples/04-store-info.md) | Address, opening hours and shipping rules from the manual. |
| [`05-scope-and-privacy.md`](examples/05-scope-and-privacy.md) | Accessories, an off-topic request, a prompt-injection attempt and another customer's order. |

## Tests

```bash
uv run pytest
```

The 102 tests run offline and need no API key. They cover the data loader, the four tools (prices, promotions, installments, availability, order lookup and its privacy rules, the policy sections), the system prompt, the answer checks and the chat loop.

## Known limitations

- **Order lookup is not real authentication.** Whoever knows a customer's e-mail or phone number can read that customer's orders. The tool answers the same way for an order that does not exist and one that belongs to someone else. A production version would verify the customer through the WhatsApp number of the conversation or a one-time code.
- **The default model sometimes drops the space between two words** (for example "valoré" or "12xsem"), and it is not deterministic. The conversations in [`examples/`](examples/) are left exactly as the agent wrote them, so a few of these slips appear there. The default is `gemini-3.5-flash-lite` because it fits the free tier's daily request limit; a more robust model, chosen with `GEMINI_MODEL`, should handle this.
- **The answer check covers prices only.** It does not verify stock counts, dates or how the policy text is paraphrased, so the model can still add a small unsupported detail (example 4 says the shipping fee is calculated "on the site", which the manual does not say).
- **Product search matches whole words,** ignoring case and accents. The model usually retries with the right spelling, but the tool itself is not fuzzy.
- **Holidays are not modeled.** The agent knows the weekly hours and asks the customer to confirm on a holiday.
- **The history lives only in memory.** There is no persistence, no per-customer session and no WhatsApp integration; it is a command-line prototype.
- **The agent cannot hand a case to a person.** Manual 7.3 asks to register and forward complaints; the agent gives the store's contact channels instead.
- **Free-tier limits apply.** Requests per minute and per day vary per account and a customer message can use several calls.

## What I would do with more time

- **Hand-off to a human.** A tool that opens a ticket for the team, which answers within 24 business hours (manual 7.3), so the agent can forward a case instead of only pointing to the channels.
- **An evaluation set.** The manual test conversations (promotions, installments, returns, hours, privacy, scope) turned into scripted cases with the facts each reply must contain, run against the real model to catch regressions when the prompt or the model changes.
- **A more robust model and wider answer checks.** Try a larger model for the slips above, and extend the price check to stock, dates and percentages.
- **Fuzzy product search,** so a typo such as "yamha" or a synonym finds the product without relying on the model to correct it.
- **Real customer verification and a real channel:** the WhatsApp number of the conversation or a one-time code, behind the WhatsApp Business API, with the history persisted per customer.
- **Observability.** Structured logs of every lookup, answer check and retry, plus token and latency metrics.
- **A holiday calendar** for the opening hours, and streaming replies for a faster feel.
- **Retrieval for the manual, only if it outgrows a topic list.** Embeddings per passage behind the same `get_policy` interface; today a topic lookup is simpler and exact.

## Use of AI assistants

I used [Cursor](https://cursor.com) to write documentation, write tests, validate the pipeline and draft parts of the code, which I reviewed and ran.

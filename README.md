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

Run the tests with `uv run pytest`.

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


## Known limitations

- **Order lookup is not real authentication.** Whoever knows a customer's e-mail or phone number can read that customer's orders. The tool answers the same way for an order that does not exist and one that belongs to someone else. A production version would verify the customer through the WhatsApp number of the conversation or a one-time code.

- **The default model sometimes drops the space between two words** (for example "valoré" or "12xsem"). The conversations in [`examples/`](examples/) are real sessions, left exactly as the agent wrote them, so a few of these slips appear there. The default is `gemini-3.5-flash-lite` because it fits the free tier's daily request limit; a more robust model, chosen with `GEMINI_MODEL`, should handle this.

## Next steps

- **Hand-off to a human.** The agent cannot register a complaint or forward a case (manual 7.3 asks for both), so it gives the store's contact channels instead and never says it forwarded anything. A production version needs a tool that opens a ticket for the team, which answers within 24 business hours.

## Status

Done: `src/emporio/data.py` turns the CSVs into typed records, and `src/emporio/tools.py` has the catalog tools (`search_products`, `get_product`) the order tool (`get_customer_orders`) and the policy tool (`get_policy`), which serves one section of the store manual at a time (`src/emporio/policies.py` splits the PDF). `src/emporio/agent.py` gives these tools and the service persona to Gemini (`gemini-3.5-flash-lite` by default, or the model named in `GEMINI_MODEL`), which decides by itself when to call them. `src/emporio/cli.py` is the command-line chat: copy `.env.example` to `.env` (it is gitignored), put your `GEMINI_API_KEY` in it and run `uv run emporio`. The history lasts only while the program runs, each consultation the agent makes is printed as `[consulta] ...`, and `sair` ends the chat. A failure (API error, no internet) does not end the conversation, and an empty answer is asked again once. `GEMINI_THINKING_LEVEL` (`low`, `medium`, `high`) is an optional setting for how much the model reasons before answering.

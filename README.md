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
- **`specs` stays a dictionary,** because its keys depend on the product category.

## Known limitations

- **Search matches whole words, not similar spellings.** A query has to appear in the product's name, description or category, ignoring accents and case. A typo such as "yamha" returns nothing.
- **Order lookup is not real authentication.** Whoever knows a customer's e-mail or phone number can read that customer's orders. The tool answers the same way for an order that does not exist and one that belongs to someone else. A production version would verify the customer through the WhatsApp number of the conversation or a one-time code.

## Status

Done: `src/emporio/data.py` turns the CSVs into typed records, and `src/emporio/tools.py` has the catalog tools (`search_products`, `get_product`) and the order tool (`get_customer_orders`). The policy tool and the agent itself are not implemented yet.

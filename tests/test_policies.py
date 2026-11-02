"""Policy lookup: the manual is split into its numbered sections, and the model gets only the one it asks for."""

import pytest

from emporio.policies import HEADINGS, PAGE_HEADER, load_policies
from emporio.tools import POLICY_TOPICS, get_policy


def test_every_section_of_the_manual_is_found_and_not_empty():
    policies = load_policies()

    assert set(policies) == set(HEADINGS)
    assert all(len(text.splitlines()) > 1 for text in policies.values())  # the heading plus a body


def test_each_section_starts_at_its_own_heading_and_stops_before_the_next():
    policies = load_policies()

    for key, heading in HEADINGS.items():
        assert policies[key].splitlines()[0] == heading
    other_headings = [h for h in HEADINGS.values() if h != HEADINGS["payment"]]
    assert not any(heading in policies["payment"] for heading in other_headings)


def test_page_headers_and_footers_are_removed():
    for text in load_policies().values():
        assert PAGE_HEADER not in text
        assert not any(line.startswith("Página ") for line in text.splitlines())


@pytest.mark.parametrize(
    "key, expected",
    [
        ("hours", ["Segunda a Sexta-feira 09:00 às 18:00", "Sábado 09:00 às 13:00", "Domingo e Feriados Fechado"]),
        ("payment", ["PIX Pagamento à vista 5% de desconto", "parcela mínima de R$ 80,00"]),
        ("returns", ["7 (sete) dias corridos", "30 (trinta) dias corridos"]),
        ("shipping", ["Frete grátis para pedidos acima de R$ 500,00", "taxa fixa de R$ 35,00"]),
        ("promotions", ["não são cumulativas"]),
        ("warranty", ["90 (noventa) dias"]),
        ("about", ["Rua 14 de Maio, 3200"]),
    ],
)
def test_sections_keep_the_rules_the_agent_needs(key, expected):
    text = " ".join(load_policies()[key].split())  # the PDF wraps lines mid-sentence

    for phrase in expected:
        assert phrase in text


def test_table_rows_stay_on_their_own_line():
    assert "Cartão de Crédito Até 12x sem juros Parcela mínima de R$ 100,00" in load_policies()["payment"].splitlines()


def test_get_policy_returns_the_section_with_its_title():
    result = get_policy("hours")

    assert result["section"] == "2. Horário de Funcionamento"
    assert "09:00 às 18:00" in result["text"]


def test_get_policy_does_not_expose_internal_sections():
    # service guidelines go into the system prompt; the final provisions are of no use to a customer
    assert set(POLICY_TOPICS) == {"about", "hours", "payment", "returns", "shipping", "promotions", "warranty", "privacy"}


def test_unknown_topic_gets_the_valid_ones():
    result = get_policy("fofoca")

    assert result["error"] == "unknown topic"
    assert set(result["valid_topics"]) == set(POLICY_TOPICS)

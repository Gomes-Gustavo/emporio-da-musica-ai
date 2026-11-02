"""Split the store policy manual (a PDF) into its numbered sections."""

import re
from functools import cache

from pypdf import PdfReader

from emporio.data import DATA_DIR

POLICY_PDF = DATA_DIR / "políticas_da_loja.pdf"
PAGE_HEADER = "Empório da Música Manual de Políticas e Procedimentos"

# The manual has ten numbered sections: each heading is a line of its own.
HEADINGS = {
    "about": "1. Sobre a Empório da Música",
    "hours": "2. Horário de Funcionamento",
    "payment": "3. Formas de Pagamento",
    "returns": "4. Política de Trocas e Devoluções",
    "shipping": "5. Política de Frete e Entregas",
    "promotions": "6. Promoções e Descontos",
    "service": "7. Atendimento via WhatsApp",
    "warranty": "8. Garantia",
    "privacy": "9. Privacidade e Proteção de Dados",
    "final": "10. Disposições Finais",
}


@cache
def load_policies() -> dict[str, str]:
    """Section key -> its text, starting with its heading. Raises if a heading is missing."""
    lines = []
    for page in PdfReader(POLICY_PDF).pages:
        # layout mode keeps table rows on one line (the default gives one word per line)
        for raw in page.extract_text(extraction_mode="layout").splitlines():
            line = " ".join(raw.split())
            if line and line != PAGE_HEADER and not re.fullmatch(r"Página \d+", line):
                lines.append(line)

    starts = {key: lines.index(heading) for key, heading in HEADINGS.items()}
    ends = sorted(starts.values())[1:] + [len(lines)]
    end_of = dict(zip(sorted(starts.values()), ends))
    return {key: "\n".join(lines[start : end_of[start]]) for key, start in starts.items()}

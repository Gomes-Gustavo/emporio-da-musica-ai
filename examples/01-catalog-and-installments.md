# Example 1: Catalog search, price and installments

What it shows: a budget search (12 matches, the 10 cheapest listed), one product in detail, and an installment question answered from the store's rule (the minimum installment of each range).

Recorded on 2026-11-03 with `gemini-3.5-flash-lite`, unedited. Lines starting with `[consulta]` are the command-line trace of the lookups the agent made; the customer does not see them.

```text
Empório da Música - atendimento (digite 'sair' para encerrar)
Você: Quais violões vocês têm até R$ 1000?
  [consulta] search_products(category='Violões', max_price=1000)
Atendente: Vi aqui que temos várias opções legais de violões até R$ 1.000! Como temos 12 modelos nessa faixa, separei os 10 mais em conta para você dar uma olhada:

- *Tagima Memphis AC-39 Nylon Natural*: R$ 429,90 (ou R$ 408,41 no PIX, ou em até 5x de R$ 85,98 no cartão)
- *Rozini RC-104 Nylon Estudante*: R$ 459,90 (ou R$ 436,91 no PIX, ou em até 5x de R$ 91,98 no cartão)
- *Shelby SN-100 Folk Aço Preto*: R$ 549,00 (ou R$ 521,55 no PIX, ou em até 6x de R$ 91,50 no cartão)
- *Giannini GF-1R Aço Folk Sunburst*: R$ 579,90 (ou R$ 550,91 no PIX, ou em até 6x de R$ 96,65 no cartão)
- *Yamaha C40 Nylon Natural*: R$ 599,90 (ou R$ 569,91 no PIX, ou em até 6x de R$ 99,98 no cartão)
- *Giannini GN-15 Nylon Cedr Natural*: R$ 689,00 (ou R$ 654,55 no PIX, ou em até 6x de R$ 114,83 no cartão)
- *Yamaha F310 Aço Natural*: R$ 699,90 (ou R$ 664,91 no PIX, ou em até 6x de R$ 116,65 no cartão)
- *Tagima Dallas Tuner Aço Natural*: R$ 749,00 (ou R$ 711,55 no PIX, ou em até 7x de R$ 107,00 no cartão)
- *Shelby SGD-195E Elétrico Aço Sunburst*: R$ 799,00 (ou R$ 759,05 no PIX, ou em até 7x de R$ 114,14 no cartão)
- *Yamaha C70 Nylon Natural*: R$ 849,00 (ou R$ 806,55 no PIX, ou em até 8x de R$ 106,13 no cartão)

Tem preferência por cordas de nylon ou de aço, ou algum modelo específico que chamou sua atenção? Precisa de mais alguma coisa?
Você: Me fale mais do Yamaha C40
  [consulta] get_product(name_or_id='Yamaha C40')
Atendente: O *Yamaha C40 Nylon Natural* é um clássico super recomendado para estudantes e iniciantes, com excelente projeção sonora!

Olha só as especificações dele:
- Cordas de nylon
- Tampo em Spruce
- Fundo e laterais em Meranti
- Braço em Nato
- Escala de 650mm
- Não é elétrico (sem captação)
- Cor: Natural

Ele custa R$ 599,90, mas sai por R$ 569,91 no PIX. No cartão, dá para parcelar em até 6x de R$ 99,98 sem juros. Vi aqui que temos estoque disponível dele.

O que achou? Precisa de mais alguma coisa?
Você: dá pra parcelar em 12x?
  [consulta] get_policy(topic='payment')
Atendente: O parcelamento no cartão de crédito pode ser feito em até 12x sem juros, mas temos uma regra de parcela mínima para cada faixa: para parcelar de 7x a 12x, a parcela mínima precisa ser de R$ 100,00.

Como o Yamaha C40 custa R$ 599,90, o máximo de parcelas sem juros para ele é em até 6x de R$ 99,98, pois em 7x ou mais a parcela ficaria abaixo do valor mínimo exigido para essa faixa.

Precisa de mais alguma coisa?
Você: sair
Atendente: Até logo!
```

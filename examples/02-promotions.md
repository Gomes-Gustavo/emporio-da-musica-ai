# Example 2: Ended promotion, active promotion and PIX

What it shows: an ended promotion reported as ended (Takamine GD20), an active promotion with its final price (Crafter HT-100), and the rule that the PIX discount does not stack on a promotion.

Recorded on 2026-11-03 with `gemini-3.5-flash-lite`, unedited. Lines starting with `[consulta]` are the command-line trace of the lookups the agent made; the customer does not see them.

```text
Empório da Música - atendimento (digite 'sair' para encerrar)
Você: Quanto custa o Takamine GD20? Tem promoção?
  [consulta] get_product(name_or_id='Takamine GD20')
Atendente: Vi aqui que o Takamine GD20 Dreadnought Natural custa R$ 2.199,00, podendo ser parcelado em até 12xsem juros de R$ 183,25 no cartão de crédito. Se preferir pagar no PIX, sai por R$ 2.089,05.

Sobre promoção, ele teve uma oferta especial de 12% de desconto que já foi encerrada, então no momento o valoré esse.

Precisa de mais alguma coisa?
Você: E o Crafter HT-100, tem promoção?
  [consulta] get_product(name_or_id='Crafter HT-100')
Atendente: O Crafter HT-100 Folk Aço Natural está em promoção! O preço original é R$ 2.399,00, mas com o Desconto Exclusivo de 18%, ele sai por R$ 1.967,18.

Você pode parcelar em até 12x sem juros de R$ 163,93 no cartão de crédito. Como ele já está com desconto de promoção, o valor no PIX é o mesmo do preço final (R$ 1.967,18), pois os descontos não são cumulativos.

Precisa de mais alguma coisa?
Você: Realmente não consegue nenhum desconto no pix?
Atendente: Como o Crafter HT-100 já está com o desconto promocional de 18% aplicado, o sistema não acumula outros descontos, então o valor no PIX é o mesmo do preço final da promoção (R$ 1.967,18).

Precisa de mais alguma coisa?
Você: sair
Atendente: Até logo!
```

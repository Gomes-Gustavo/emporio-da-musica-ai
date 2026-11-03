# Example 4: Address, opening hours and shipping

What it shows: store data and rules answered from the policy manual: the address, Saturday hours, whether the store is open right now, and the shipping fees and times for Campo Grande and for other cities. It was recorded on a Tuesday during opening hours, which is why the agent says the store is open.

Recorded on 2026-11-03 with `gemini-3.5-flash-lite`, unedited. Lines starting with `[consulta]` are the command-line trace of the lookups the agent made; the customer does not see them.

```text
Empório da Música - atendimento (digite 'sair' para encerrar)
Você: Qual o endereço de vocês?
  [consulta] get_policy(topic='about')
Atendente: Ficamos na *Rua 14 de Maio, 3200 — Centro, Campo Grande - MS*.

Precisa de mais alguma coisa?
Você: Que horas vocês abrem no sábado?
  [consulta] get_policy(topic='hours')
Atendente: No sábado, abrimos das *09:00 às 13:00*.

Precisa de mais alguma coisa?
Você: Vocês estão abertos agora?
  [consulta] get_policy(topic='hours')
Atendente: Sim, estamos abertos! Hoje, terça-feira, nosso atendimento vai até as 18:00.

Precisa de mais alguma coisa?
Você: Quanto é o frete pra Campo Grande? E pra Dourados?
  [consulta] get_policy(topic='shipping')
Atendente: Para **Campo Grande**, o frete é grátis para pedidos acima de R$ 500,00. Para pedidos abaixo de R$ 500,00, a taxa fixa é de R$ 35,00, com prazo de entrega de 1 a 3 dias úteis.

Para **outras cidades** como Dourados, utilizamos Correios (PAC e SEDEX) e a transportadora Jadlog. O valor dofrete para lá é calculado automaticamente no site de acordo com o CEP de destino, peso e dimensões do produto.Os prazos estimados são:
- *PAC (Correios)*: 5 a 12 dias úteis
- *SEDEX (Correios)*: 2 a 5 dias úteis
- *Jadlog (.package)*: 3 a 8 dias úteis

Precisa de mais alguma coisa?
Você: sair
Atendente: Até logo!
```

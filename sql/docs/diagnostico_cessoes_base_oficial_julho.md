# Cessões de direito e base oficial de julho — diagnóstico e decisões

**Data:** 11/08/2026
**Autor:** Pedro Moura (com assistência de agente)
**Escopo:** Sorteio 5 Casas & 1 Milhão — tratamento de contratos transferidos
(cessão de direito), quitados e distratados nas bases do painel e do
fechamento mensal.

---

## 1. Contexto

Pergunta original: contratos transferidos (cessões) entram na base do
sorteio? Se o cessionário paga, ele precisa constar como apto — inclusive
na foto mensal (snapshot).

## 2. Mecânica da cessão no UAU (validada com dados em 11/08/2026)

Fontes: vault de conhecimento UAU + `sql/validacao_cessoes.sql` +
`sql/Resultados/validacao_cessoes.xlsx` (execução na origem).

- Cessão de direito = `VendaHist.TipoMnt_vhist = 2` aprovada
  (`DataAprovacao_vhist IS NOT NULL`). **Gera venda NOVA**
  (`NumNovaVend_vhist`) no nome do cessionário, na mesma empresa/obra.
- A venda **antiga migra para `VendasRecebidas` com status 1 (cancelada)**
  — 100% dos 729 casos da campanha (01/07 a 10/08). Some de qualquer base
  filtrada por `Status_Ven = 0`.
- Cessão **não passa por `VendaDistrato`** (zero sobreposição, medição
  06/08) — o `NOT EXISTS` de distrato não afeta cessões.
- `Vendas.DataCessao_Ven` é preenchida na venda **nova** (oriunda de
  cessão), nunca na cedida — corrige leitura invertida de BIs antigos.
- Volumetria: 73.108 cessões aprovadas no universo (obras 65-69);
  729 na campanha até 10/08. Das vendas novas: 82% ativas (status 0),
  17,5% já quitadas (status 3), 5 canceladas (cessão em cadeia).
- Existe `dbo.fn_UltimaVendaCessaoDireito` (função UAU mantida, modificada
  07/2026) que percorre a cadeia de cessões até a venda vigente.
- Suspeita registrada: recebimentos na venda antiga no ato da cessão com
  média de R$ 335k/venda — provável **baixa técnica** (não é dinheiro do
  cliente). Query de conferência:
  `sql/validacao_recebimentos_tecnicos_cessao.sql` (pendente de execução).

## 3. Decisões de negócio (11/08/2026)

1. **Cupom não transfere entre donos.** Cada um fica com o que gerou:
   cedente = cupons dos pagamentos ANTES da cessão; cessionário = cupons
   da venda nova.
2. **Contrato quitado na campanha segue concorrendo** no sorteio final
   (Milhão) com os cupons gerados.
3. **Aptidão em duas réguas:**
   - `[Aptidão Casas]` (sorteio mensal): quitadas e cedidas resgatadas só
     ficam aptas no mês em que tiveram movimentação (recebimento > 0 no
     mês); contratos normais seguem a régua de parcela vencida.
   - `[Aptidão Sorteio]` (Milhão/final): régua de parcela vencida;
     quitada/cedida segue apta com o acumulado.
4. **Distrato aprovado após o fechamento** (ex.: agosto para a base de
   julho): permanece na base de julho para auditoria, porém **NÃO APTO**
   nas duas aptidões, com motivo `DISTRATO APÓS O FECHAMENTO`. Resolve a
   pendência dos casos "sumidos" entre snapshot e reexecução.

## 4. Implementação

### `sql/query_sorteio_milhao.sql` (painel, mês vigente)

- Resgate: além de `Status_Ven = 0`, entram **quitadas (status 3)** e
  **cedidas (status 1 com cessão aprovada)** que tenham recebimento na
  campanha.
- **Corte na data da cessão:** recebimentos de venda cedida só contam com
  `Data_Rec` anterior à data da cessão (`DataMnt_vhist`) — neutraliza a
  baixa técnica por construção.
- Anti-join `Vendas × VendasRecebidas` contra duplicata de venda em
  transição.
- Colunas novas (fim do SELECT): `[Cessão]`, `[Venda Origem Cessão]`,
  `[Data Cessão]`, `[Contrato Quitado]`, `[Contrato Cedido]`,
  `[Venda Nova Cessão]`, `[Data Cedida]`, `[Aptidão Casas]`,
  `[Aptidão Sorteio]`. Total: 59 colunas (eram 50).
- Restrição preservada: zero aspas duplas (query vive em string M no
  Fabric).

### `sql/query_sorteio_milhao_julho.sql` (base oficial de julho — NOVA)

Mesma estrutura e colunas do painel + `[Distrato Após Fechamento]`
(60 colunas), com janelas travadas em julho (parâmetros `@IniCampanha`,
`@IniMes`, `@Corte` — reutilizável nos próximos meses). Substitui o
snapshot batido em 31/07 como base oficial do mês. Diferenças:

- Aptidão retroativa em 31/07 (2 fontes): parcela vencida até 31/07 sem
  baixa com `Data_Rec` < 01/08; ou paga somente a partir de 01/08.
- Distrato/cessão de agosto não derrubam quem estava ativo em julho;
  distrato pós-fechamento = NÃO APTO (decisão 4).
- Limitações documentadas no cabeçalho: valores de inadimplência e
  jurídico refletem estado atual (não afetam a régua de aptidão).

### `sql/fechamento_julho_2026_elegiveis.sql` (v4)

Encadeamento antiga↔nova (`[Venda Nova Cessao]`/`[Venda Origem Cessao]`),
flag `[Cessao Apos Fechamento]` e corte de recebimentos na data da cessão.

### `notebooks/depara_base_oficial_julho.py` (Fabric)

De-para foto de 31/07 × nova base oficial: quem saiu, quem entrou
(classificado por motivo: cessão/quitada/distrato pós/baixa tardia),
mudanças de aptidão e cupons. Saídas em
`Files/painel_milhao/depara/07_2026/`.

## 5. Validação dos exports (11/08/2026, "Querys Atualizadas.xlsx")

| Checagem | Base atual | Base julho |
|---|---|---|
| Linhas | 98.444 | 98.404 |
| Duplicata de chave | 0 | 0 |
| `Status Sorteio` ≠ `Aptidão Sorteio` | 0 | 0 |
| Quitadas resgatadas | 446 | 402 |
| Cedentes resgatados | 508 | 502 |
| Distrato pós-fechamento | — | 10 |
| Cupons Milhão | 1.045.827 | 735.486 |
| Cupons Milhão das resgatadas | 79.334 (7,6%) | 68.957 |

- Julho: Cupons Milhão = Cupons Casas (735.486) — 1º mês da campanha,
  consistência interna confirmada.
- `[Aptidão Casas]` (atual): 139 das 954 resgatadas aptas (movimentação em
  agosto), 815 não aptas — regra funcionando.
- Julho: 11 resgatadas NÃO APTAS no Sorteio — quitaram/cederam em agosto
  pagando parcela vencida de julho; régua retroativa correta.
- Diff: 98.392 contratos nas duas bases; 52 só na atual (vendas/cessões
  novas de agosto); 12 só em julho = 10 distratos pós-fechamento
  (tratados pela decisão 4) + 2 residuais com 0 cupons (família dos
  "8 sem retorno", sem impacto no sorteio; chaves: 353-67106-1436 e
  210-69705-3542).

## 6. Pendências

1. Executar `sql/validacao_recebimentos_tecnicos_cessao.sql` e confirmar a
   fronteira do corte (recebimento no dia da cessão).
2. Reexecutar a base de julho após a decisão 4 (10 distratos devem sair
   NÃO APTO) e subir ao lakehouse
   (`Files/painel_milhao/base_oficial/07_2026/`).
3. Rodar o de-para (notebook) contra a foto antiga de 31/07.
4. Adapter do painel: conferir as 9 colunas novas antes de atualizar a
   string M no Fabric.
5. Alinhar a régua de cupons/aptidão da API do site (pendência anterior,
   reforçada).
6. Investigar (baixa prioridade) os 2 contratos residuais sem
   distrato/cessão — mecanismo de venda deletada/recriada
   (`sql/investigacao_8_sem_retorno.sql`).

# Plano — Auditoria de Fechamento Mensal no Fabric

**Projeto:** Campanha 5 Casas & 1 Milhão · **Autor:** Pedro (Dados) · **Data:** 06/08/2026

## 1. Objetivo

Industrializar no Fabric o processo de fechamento mensal do sorteio que em julho/2026 foi feito manualmente: apuração retroativa do mês fechado, de-para contra a foto do dia 31, detecção de baixas tardias e geração da lista de elegíveis com trilha de auditoria.

## 2. Por que existe (aprendizado de julho)

- Pagamentos de 30–31/07 só foram baixados entre 01 e 06/08 — a foto de 31/07 ficou incompleta.
- Resultado medido no de-para: **986 clientes resgatados** (seriam excluídos indevidamente), **+47.590 cupons** vs a foto.
- `Data_Rec` preserva a data real do pagamento → o mês fechado é reconstruível a qualquer momento após as baixas.
- Não existe coluna confiável para detectar baixa tardia na base viva (`DataCad_Rec` refutada em 06/08) → o caminho é **reexecutar a apuração e comparar execuções**.

## 3. Arquitetura

```
Pipeline Fabric (agenda diária ~18h BR; roda só nos dias 1–7 do mês)
│
├─ Atividade 0: If dayOfMonth > 7 → sai sem fazer nada
│
├─ 1. Dataflow Gen2 "apuração fechamento"
│      Query retroativa parametrizada (sempre apura M-1)
│      Gateway na origem (BURITI-BD-02)
│      → Tables/fechamento_apuracao  (APPEND por execução)
│
├─ 2. Notebook "de-para fechamento"
│      Lê: foto do fechamento (notebook de snapshot existente)
│           × apuração de hoje × apuração de ontem
│      Grava: Tables/fechamento_depara (resumo/execução)
│      Calcula: estável? (execução N idêntica à N-1)
│
└─ 3. If estável:
       → gera Tables/fechamento_elegiveis (APTO + cupons > 0,
         flag resgatado_baixa_tardia)
       → alerta Teams/e-mail: "base fechou, lista pronta"
     If dia 7 e ainda instável:
       → alerta humano (NÃO fecha sozinho)
```

Workspace: `FB_Comercial` · Lakehouse: `lh_bronze_campanha_1m` (mesmo do snapshot atual).

## 4. Modelo de dados (Delta tables)

| Tabela | Grão | Chave | Escrita |
|---|---|---|---|
| `fechamento_apuracao` | venda × execução | anomes + dt_execucao + empresa/obra/venda | append |
| `fechamento_depara` | execução | anomes + dt_execucao | append |
| `fechamento_elegiveis` | venda × mês fechado | anomes + empresa/obra/venda | 1 versão por mês |

**Append, nunca sobrepor.** Cada execução preservada = trilha completa pra auditoria externa (Bruno pode pedir). A convergência entre execuções vira histórico consultável via SQL endpoint.

O snapshot atual (Files/painel_milhao/snapshot, sobrepõe) continua como está — papel diferente: foto contemporânea do dia do fechamento.

## 5. Decisões já tomadas (herdadas de julho)

1. **Corte dinâmico**: `@Corte = 1º dia do mês corrente`; `@IniMes = M-1`. Rodando dias 1–7 do mês M, apura sempre M-1. Zero hardcode.
2. **Clamp `GREATEST(0, ...)` nos cupons** — caso real de julho: estorno líquido gerou −1 cupom (venda 5530, obra 69717).
3. **Parada por estabilidade, não por dia fixo**: "fechado" = duas execuções consecutivas idênticas (counts + somas). Dia fixo é previsão, não garantia (julho provou).
4. **Gateway na origem**, mesmo padrão do dataflow da query principal. O espelho tem timing próprio de réplica e nunca foi validado pra `Recebidas` ("UAU reprocessa o passado" morde réplica incremental).
5. **Zero aspas duplas na string M** da query (pegadinha conhecida da `query_sorteio_milhao.sql`).
6. **Acesso restrito**: tabelas têm nome/CPF — permissão mínima no workspace/lakehouse, sensitivity label.
7. Regra de negócio pendente que a pipeline herda: **distrato aprovado após o fechamento** concorre ao mês fechado? (92 casos em julho — decisão Carlos/Robson). A query precisa refletir a decisão.

## 6. Ordem de implementação

| # | Etapa | Quem | Artefato |
|---|---|---|---|
| 1 | Query parametrizada M-1 (com clamp) | Claude prepara | `sql/fechamento_mensal_dataflow.sql` |
| 2 | Notebook de-para (port do script local) | Claude prepara | `notebooks/nb_depara_fechamento.py` |
| 3 | Dataflow Gen2 + tabelas destino + pipeline com agenda e Ifs | Pedro (Fabric UI) | — |
| 4 | Backfill julho: subir apuração + de-para + elegíveis como `anomes=202607` | Pedro + Claude | histórico desde o 1º mês |
| 5 | Ensaio geral: fechamento de agosto roda 01–07/09 sozinho | pipeline | Pedro só confere o alerta |

## 7. Riscos e pontos de atenção

- **Agenda "dias 1–7"**: o scheduler do Fabric é diário/semanal, sem cron por dia-do-mês. Solução: agenda diária + primeira atividade checa `dayOfMonth <= 7` e encerra limpa. Detalhe de implementação, não muda o desenho.
- **Arquivo de retorno perdido** (aconteceu em julho): pagamento sem baixa nunca aparece — o critério de estabilidade não detecta o que nunca chegou. Mitigação: alerta do dia 7 + acompanhamento do time de baixas (Maranhão).
- **Custas (Tipo '1') na régua de aptidão**: decisão pendente (hoje inclui, igual ao painel). Se mudar, ajustar query do dataflow e a principal juntas.
- **Janela 8h/15h do espelho** não se aplica aqui (roda na origem), mas o painel Streamlit que exibir essas tabelas herda a defasagem normal do OneLake.

## 8. Fora de escopo (por enquanto)

- Automatizar o envio da lista ao Bruno (fica manual, por canal seguro, após validação humana).
- Sorteio das Casas × Milhão em pipelines separadas — mesma apuração serve às duas por ora.
- Exclusão de CPFs de sócios/colaboradores na query (regra aplicada no momento do sorteio; lista ainda com Robson/Jeicia).

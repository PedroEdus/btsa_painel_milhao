# Status do Projeto — Painel da Campanha do Milhão

Atualizado em: **06/07/2026 17:18**

Este documento registra o que já foi implementado no MVP do **Painel da Campanha do Milhão** até o momento, com base no código atual, documentação existente e histórico de commits do repositório.

Documentos relacionados:

- `README.md` — visão rápida, execução local, deploy, autenticação e regra de cupom.
- `CONTEXT_PAINEL_DO_MILHAO.md` — contexto de negócio, decisões, riscos e pendências vindas das reuniões.
- `DESIGN.md` — identidade visual e tokens derivados do CGID / Brasil Terrenos.

---

## 1. Resumo executivo

O projeto já possui um MVP funcional em **Streamlit** para acompanhamento executivo da Campanha do Milhão da Brasil Terrenos.

O painel:

- consome snapshot Parquet no **Microsoft Fabric / OneLake**;
- adapta o snapshot bronze para um schema interno estável;
- valida colunas obrigatórias e duplicidades relevantes antes de exibir os dados;
- apresenta indicadores executivos, funil, análises por cidade, matriz de participação, indicadores de inadimplência e matriz de exportação;
- diferencia explicitamente **cupons calculados internamente** de **cupons oficiais** da plataforma externa;
- possui cache por janela de atualização da base, alinhado aos horários de carga do Fabric;
- tem identidade visual customizada com marca Brasil Terrenos, responsividade mobile e modo TV;
- possui camada de autenticação OIDC pronta, porém desligada por padrão;
- tem testes automatizados para regra de cupom, janela de atualização e validação de contrato.

---

## 2. Arquitetura atual

Fluxo implementado:

```text
UAU / origem operacional
        ↓
Consulta e consolidação pelo time de dados
        ↓
Microsoft Fabric / OneLake
        ↓
Snapshot Parquet em Lakehouse
        ↓
data.onelake.load_painel_milhao_data()
        ↓
data.adapter.adaptar()
        ↓
data.repository.carregar_dados()
        ↓
services.validation.validar()
        ↓
services.metrics + app.py
        ↓
Streamlit com tabs executivas
```

Diretrizes já respeitadas:

- o painel **não conecta diretamente ao banco operacional do UAU**;
- a aplicação lê uma camada de consumo/snapshot no Fabric;
- regras financeiras e métricas ficam em `services/metrics.py`, não espalhadas na UI;
- contrato de dados fica centralizado em `data/contract.py`;
- transformação da origem fica centralizada em `data/adapter.py`;
- credenciais não são codificadas no código-fonte: vêm de `st.secrets` ou `.env`.

---

## 3. Estrutura do repositório

```text
app.py                         # Entry point Streamlit; single-page com tabs
components/
  format.py                    # Formatação BR + mascaramento de CPF/telefone/e-mail
  theme.py                     # CSS, tokens visuais e template Plotly
  ui.py                        # Componentes visuais, gráficos, tabelas, modo TV
config/
  settings.py                  # Parâmetros de campanha, atualização, auth e regra de cupom
data/
  contract.py                  # Contrato interno de colunas e chaves
  adapter.py                   # Tradução do snapshot bronze para schema interno
  onelake.py                   # Download/leitura de snapshot Parquet no OneLake
  repository.py                # Cache por janela 8h/15h BR e ponto único de acesso
services/
  auth.py                      # Gate de login Google/OIDC por domínio/e-mail permitido
  metrics.py                   # Regra de cupom, KPIs e agregações
  validation.py                # Validação de base vazia, obrigatórias e duplicidade
tests/
  test_metrics.py              # Regra de cupom e KPIs
  test_repository.py           # Janelas de atualização 8h20/15h20
  test_validation.py           # Contrato, base vazia e duplicidades
scripts/
  baixar_snapshot.py           # Script auxiliar de snapshot
assets/
  logo_branca.png
  logo_preta.png
.streamlit/
  config.toml
  secrets.toml.example
```

---

## 4. Integração de dados

### 4.1 OneLake / Fabric

Implementado em `data/onelake.py`:

- autenticação por **Azure Service Principal** usando:
  - `AZURE_TENANT_ID`;
  - `AZURE_CLIENT_ID`;
  - `AZURE_CLIENT_SECRET`;
- leitura de secrets via `st.secrets` com fallback para `.env` local;
- conexão no endpoint `https://onelake.dfs.fabric.microsoft.com`;
- workspace configurado como `FB_Comercial`;
- snapshot em:

```text
lh_bronze_campanha_1m.Lakehouse/Files/painel_milhao/snapshot/painel_milhao_snapshot
```

- listagem dinâmica da pasta para localizar arquivos `.parquet`;
- leitura de todos os `part-*.parquet`, não apenas o primeiro arquivo;
- concatenação dos parts quando o Spark particiona o snapshot;
- tratamento visual de erro via `st.error()` + `st.stop()`.

### 4.2 Adapter do snapshot bronze

Implementado em `data/adapter.py`:

- normalização de nomes de coluna para `snake_case` sem acento;
- suporte a valores monetários em formato BRL string ou numérico;
- mapeamento de colunas da query para o schema interno;
- suporte ao formato novo da query 07/2026;
- leitura de cupons pré-calculados pelo Fabric (`cupons_milhao` / fallback `cupons_gerados`);
- preservação de `valor_gera_cupom` como `valor_elegivel` quando disponível;
- normalização de obra, empresa, regional, telefone e datas;
- derivação de `mes_referencia` pela data de recebimento;
- conversão de `status_sorteio` em:
  - `status_elegibilidade = elegivel | pendente`;
  - `status_cadastro = cadastrado | nao_cadastrado`;
- defaults para decomposição financeira ainda não disponível no bronze:
  - `valor_principal` = `valor_total_recebido`;
  - multa, juros e custas = `0.0`;
- suporte a classificação de recuperação por:
  - coluna explícita `recuperacao` no snapshot atual;
  - fallback `inadimplente_no_mes_pago`;
  - fallback fraco `pagou_parcela_mes_anterior` + status apto;
- cálculo de `valor_recuperado` como valor recebido por linhas classificadas como recuperação;
- compatibilidade com `diasatraso` para `dias_atraso`.

### 4.3 Estado atual não commitado

No momento deste documento, existe uma alteração local em `data/adapter.py`:

- preferência pela coluna explícita `recuperacao` quando ela existe;
- `valor_recuperado` passou a ser derivado dos pagamentos classificados como recuperação;
- suporte inicial à coluna `inad_junho` para status de inadimplência no início da campanha.

Atenção técnica: revisar antes do commit se o preenchimento final de `status_inadimplencia_antes` não está sobrescrevendo o valor derivado de `inad_junho`.

---

## 5. Contrato e validação

### 5.1 Contrato de dados

Implementado em `data/contract.py`:

- schema interno esperado pelo painel;
- granularidade documentada:

```text
empresa x obra x venda x cpf_titular x mes_referencia
```

- chaves:
  - `CHAVE_VENDA = (empresa, obra, num_venda)`;
  - `CHAVE_GRAO = (empresa, obra, num_venda, cpf_titular, mes_referencia)`;
- colunas obrigatórias mínimas para o painel rodar.

O contrato cobre:

- identificação de venda/cliente;
- financeiro;
- elegibilidade/cadastro/cupons;
- inadimplência/recuperação.

### 5.2 Validação

Implementado em `services/validation.py`:

- falha explícita para base vazia;
- erro quando faltam colunas obrigatórias;
- alerta para duplicidade no grão quando o volume passa de 1%;
- alerta para nulos em colunas financeiras críticas.

A validação é chamada no início do `app.py`. Se houver erro crítico, o painel exibe os erros e interrompe a renderização.

---

## 6. Atualização e cache

Implementado em `data/repository.py` e `components/ui.py`.

### 6.1 Janelas de atualização

A base do Fabric é considerada atualizada em duas janelas nominais, no fuso de Brasília:

- 08h;
- 15h.

O painel usa margem padrão de 20 minutos (`ATUALIZACAO_MARGEM_MINUTOS`) para esperar o pipeline terminar de gravar o snapshot:

- busca efetiva da janela das 08h ocorre a partir de 08h20;
- busca efetiva da janela das 15h ocorre a partir de 15h20.

### 6.2 Cache

- `data.repository._carregar()` usa `st.cache_data`;
- o cache é keyado pela janela vigente (`janela_atual().isoformat()`);
- a aplicação não depende de TTL curto ou refresh a cada poucos minutos;
- ao virar a janela, uma nova chave força nova leitura do OneLake.

### 6.3 Auto-refresh

- `components.ui.auto_refresh()` agenda reload completo da página na próxima janela de atualização;
- o reload recria a sessão, invalida o contexto visual antigo e permite buscar dados novos;
- a marcação “Atualizado” no header usa o horário nominal da janela vigente.

---

## 7. Regra de cupom e métricas

Implementado em `config/settings.py` e `services/metrics.py`.

### 7.1 Parâmetros de cupom

`RegraCupom` centraliza:

- versão da regra: `v1-2026-06`;
- valor por cupom: `R$ 100,00`;
- componentes elegíveis:
  - principal;
  - multa;
  - juros;
  - custas, controlado por `CUPOM_INCLUIR_CUSTAS`;
- arredondamento por blocos completos (`floor(valor / 100)`), descartando saldo residual enquanto a regra não for alterada.

### 7.2 Cupons calculados vs oficiais

Já está documentado e exibido no painel que:

- `cupons_calculados` são calculados internamente ou vindos pré-calculados pelo Fabric;
- `cupons_oficiais` dependem de integração externa;
- o painel não deve apresentar números simulados como se fossem oficiais.

### 7.3 Métricas e agregações já implementadas

`services/metrics.py` possui funções para:

- valor elegível;
- cupons calculados;
- KPIs executivos;
- KPIs de carteira;
- recebimento diário e mensal;
- recebimento por classificação (`normal` x `recuperacao`);
- cupons por mês;
- cupons por cidade;
- cupons por tipo de sorteio;
- média de cupons por dia da semana;
- top obras por valor/cupons;
- inadimplência por faixa de atraso;
- inadimplência por cidade;
- funil de participação;
- calendário de sorteios;
- progresso temporal da campanha;
- novos clientes pela primeira venda após início da campanha, quando `data_venda` existe.

---

## 8. Interface Streamlit implementada

O `app.py` é uma página única com `st.tabs()` e seis abas principais.

### 8.1 Visão Geral

Inclui:

- banner de premiação;
- hero de arrecadação;
- cupons do Milhão;
- cupons de casas;
- participantes;
- cidades participantes;
- sorteios realizados;
- dias restantes;
- nota explícita da regra de cupom e da diferença entre calculado e oficial;
- KPIs de cadência e abrangência:
  - cupons/dia;
  - novos clientes;
  - saldo inadimplente;
  - dias médios em atraso;
  - parcela média paga;
  - valor recuperado;
- comparação consolidada de adimplentes x inadimplentes;
- progresso de adimplência.

### 8.2 Análise por Cidade

Inclui:

- cidades participantes;
- média de cupons por cidade;
- média de elegíveis por cidade;
- média de inadimplentes por cidade;
- gráfico de cupons por regional;
- gráfico de recebimento por regional;
- tabela de participação por cidade com:
  - clientes;
  - elegíveis;
  - pendentes;
  - percentual de clientes;
  - cupons;
  - percentual de cupons;
  - valor recebido.

### 8.3 Funil da Campanha

Inclui:

- estatísticas de arrecadação, meta temporal e taxa de cadastro/elegibilidade;
- alternância entre visão diária e mensal do recebimento;
- linha temporal de recebimento acumulado;
- barras de recebimento mensal;
- funil de participação;
- cupons por mês;
- donut normal x recuperação.

### 8.4 Matriz de Participação

Inclui:

- resumo por obra e elegibilidade;
- ranking dos 15 clientes com maior volume de cupons;
- tabelas com status visual;
- comportamento adaptado para desktop e mobile.

### 8.5 Indicadores Executivos

Inclui:

- ticket médio por venda;
- cupons por cliente apto;
- taxa de elegibilidade;
- novos clientes;
- valor recuperado;
- medidor de aproveitamento dos cupons;
- inadimplência por faixa de atraso;
- média de cupons por dia da semana;
- cupons por tipo de sorteio.

### 8.6 Exportação

Inclui matriz hierárquica por:

```text
regional → cidade → empresa → produto
```

A matriz apresenta:

- clientes;
- elegíveis;
- inadimplentes;
- cupons;
- valor recebido;
- drill-down nativo com `<details>/<summary>`;
- botão para baixar CSV (`matriz_exportacao.csv`);
- fragmento Streamlit para evitar que o clique de download reinicie a navegação para a primeira aba.

---

## 9. Componentes visuais e UX

### 9.1 Design system

Implementado em `components/theme.py` e documentado em `DESIGN.md`:

- paleta Brasil Terrenos com verde primário `#2a9d45`;
- vermelho da marca `#e2231a`;
- semânticas de danger/warning/info;
- tokens de raio, sombra, borda e superfícies;
- template Plotly próprio;
- CSS global para reduzir chrome padrão do Streamlit.

### 9.2 Componentes implementados

Em `components/ui.py`:

- header de página;
- logo e tema;
- splash de abertura;
- auto-refresh;
- modo TV / autoplay de abas;
- cards de KPI;
- hero;
- cards genéricos;
- badges;
- medidor/gauge;
- funil;
- donut;
- linha temporal;
- barras verticais/horizontais;
- barras regionais com escala visual;
- ranking de cidades;
- calendário de sorteios;
- banner de premiação;
- tabelas desktop/mobile;
- estilos de célula por status.

### 9.3 Responsividade e mobile

Já foram feitos vários ajustes para mobile:

- breakpoints para telas pequenas;
- tabelas HTML no mobile com primeira coluna fixa;
- scroll horizontal interno;
- cabeçalho fixo em tabelas HTML;
- colunas mais estreitas para caber mais informação;
- truncamento com reticências;
- toque/foco para expandir nome de produto/obra sem cobrir colunas vizinhas;
- ajuste específico da matriz de exportação para mobile.

### 9.4 Modo TV

Já foi implementado:

- auto-rotação das abas a cada 10 segundos;
- botão play/pause no header;
- modo TV desligado por padrão ao abrir;
- remoção da barra de progresso visual do modo TV;
- layout ajustado para caber em fullscreen 1080p sem scroll em áreas críticas.

---

## 10. Autenticação, segurança e LGPD

### 10.1 Auth

Implementado em `services/auth.py`:

- autenticação nativa do Streamlit via OIDC (`st.login`, `st.user`, `st.logout`);
- login Google;
- verificação server-side de e-mail verificado;
- autorização por domínios e/ou e-mails configuráveis:
  - `ALLOWED_EMAIL_DOMAINS`;
  - `ALLOWED_EMAILS`;
- fallback para domínio `btsa.com.br`;
- `AUTH_ENABLED=false` por padrão;
- fail-closed se auth estiver ligada e a seção `[auth]` não estiver configurada.

### 10.2 Dados sensíveis

Implementado em `components/format.py`:

- mascaramento de CPF;
- mascaramento de telefone;
- mascaramento de e-mail.

Pontos de atenção mantidos:

- a base pode conter CPF, telefone, e-mail e valores financeiros;
- qualquer publicação em ambiente terceiro precisa de avaliação de segurança/LGPD;
- dados oficiais de cupons dependem de integração externa e não devem ser simulados.

---

## 11. Deploy e execução local

### 11.1 Execução local

Documentado no `README.md`:

```bash
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Variáveis relevantes:

- `AZURE_TENANT_ID`;
- `AZURE_CLIENT_ID`;
- `AZURE_CLIENT_SECRET`;
- `AUTH_ENABLED`;
- `ALLOWED_EMAIL_DOMAINS`;
- `ALLOWED_EMAILS`;
- `META_ARRECADACAO`;
- `CUPOM_INCLUIR_CUSTAS`;
- `ATUALIZACAO_MARGEM_MINUTOS`;
- `CUPONS_DISPONIVEIS`.

### 11.2 Deploy Streamlit Community Cloud

Já documentado no `README.md` como alternativa de validação:

- apontar o app para `app.py`;
- preencher `secrets.toml` pelo painel de Secrets;
- manter `.env` e `secrets.toml` fora do Git;
- restringir acesso se auth for habilitada.

Observação: Community Cloud não deve ser assumido como ambiente definitivo para dados reais sem validação jurídica/segurança.

---

## 12. Testes automatizados

Framework: `pytest`.

Testes existentes:

### 12.1 `tests/test_metrics.py`

Cobre:

- R$ 244 gerando 2 cupons e descartando residual;
- R$ 1.000 gerando 10 cupons;
- soma de componentes elegíveis;
- exclusão de custas quando flag desligada;
- registro da versão da regra;
- contagem de clientes únicos em KPIs.

### 12.2 `tests/test_repository.py`

Cobre:

- janela das 08h ao meio-dia;
- janela das 15h à noite;
- madrugada usando 15h do dia anterior;
- margem de 20 minutos após a fronteira;
- próxima atualização sempre posterior ao horário atual.

### 12.3 `tests/test_validation.py`

Cobre:

- base sintética mínima com obrigatórias;
- falha para base vazia;
- base válida;
- falha por coluna obrigatória ausente;
- aviso para duplicidade no grão;
- cor visual de status na tabela.

---

## 13. Linha do tempo do que foi feito

Principais marcos extraídos do histórico de commits:

1. Criação do dashboard executivo da Campanha do Milhão em Streamlit.
2. Migração para leitura via OneLake / Parquet, removendo dependência de `pyodbc` e `packages.txt` obsoleto.
3. Ajustes iniciais de UI: datas em pt-BR, cards, donut e tooltips.
4. Responsividade mobile:
   - breakpoints;
   - tabelas com primeira coluna fixa;
   - scroll interno;
   - min-width e truncamento;
   - toque para expandir produto/obra.
5. Ocultação do chrome padrão do Streamlit e redução de FOUC.
6. Hover do recebimento diário mostrando valor do dia + acumulado.
7. Matriz de Exportação com drill-down e ajustes de tema/mês por extenso.
8. Matriz de Exportação mobile.
9. Correção em `inadimplencia_por_faixa`.
10. Atualização por janelas 08h20/15h20 BR e remoção de mock.
11. Reorganização dos Indicadores Executivos, com gráficos no topo e tabela embaixo.
12. Suporte ao novo formato de query 07/2026 e novos indicadores executivos.
13. Refinos em gráficos regionais:
    - altura;
    - labels;
    - headroom;
    - formatação monetária compacta.
14. Evoluções na visualização de inadimplência por faixa:
    - cores;
    - uso melhor da altura;
    - gradiente conforme atraso.
15. Separação no hero entre cupons do Milhão e cupons de casas.
16. Ajuste para Indicadores Executivos caberem em fullscreen 1080p sem scroll.
17. Remoção da barra de progresso do modo TV.
18. Suporte a query com coluna única `cupons_casas`, mantendo fallback para formato anterior.
19. Alteração local em andamento para recuperação explícita, valor recuperado e inadimplência de junho no adapter.

---

## 14. Pendências e pontos de atenção

### 14.1 Regras de negócio

Ainda precisam de confirmação formal:

- tratamento final de multa, juros e custas;
- regra para saldo residual menor que R$ 100;
- retroatividade de pagamentos anteriores ao cadastro/aceite;
- regra final de renegociação e antecipação;
- tratamento definitivo de múltiplos compradores;
- retirada de ganhadores dos sorteios mensais seguintes;
- reconciliação entre cupons calculados e cupons oficiais.

### 14.2 Dados

Pontos ainda dependentes do pipeline/base:

- decomposição real entre principal, multa, juros e custas;
- cadastro/aceite real, se for diferente de elegibilidade;
- cupons oficiais da plataforma externa;
- chave de reconciliação com a plataforma externa;
- validação de `recuperacao`, `inad_junho`, `cupons_casas` e demais colunas da query atual;
- confirmação da granularidade final da view do Fabric.

### 14.3 Código

Pontos técnicos para revisar:

- confirmar se `status_inadimplencia_antes` não está sendo sobrescrito no final de `data/adapter.py`;
- avaliar se tooltip de “Valor recuperado” deve deixar de dizer “não disponível” quando a coluna `recuperacao` estiver validada no snapshot;
- considerar ampliar testes para `data.adapter.adaptar()` com o formato novo da query 07/2026;
- considerar teste específico para `cupons_por_tipo()` com `cupons_casas` único e formato anterior;
- revisar se todos os campos sensíveis usados em ranking/tabelas precisam de mascaramento para o ambiente de publicação.

### 14.4 Operação

Ainda pendente definir:

- ambiente definitivo de hospedagem;
- se `AUTH_ENABLED` ficará ligado em produção;
- responsáveis pela rotação/gestão das credenciais Azure;
- processo de validação dos números com Carlos/time de negócio;
- rotina de monitoramento caso o snapshot não seja gerado na janela esperada.

---

## 15. Como verificar o projeto hoje

Com ambiente e credenciais configurados:

```bash
pip install -r requirements.txt
pytest
streamlit run app.py
```

Checklist mínimo de validação manual:

1. App abre sem erro.
2. Header mostra horário “Atualizado” coerente com a janela vigente.
3. Dados carregam do snapshot OneLake.
4. A validação não acusa colunas obrigatórias ausentes.
5. Visão Geral mostra arrecadação, cupons, participantes e cidades.
6. Nota de cupom calculado vs oficial aparece na primeira aba.
7. Abas funcionam sem reset inesperado.
8. Modo TV pode ser ativado/desativado.
9. Matriz de Exportação abre os níveis regional/cidade/empresa/produto.
10. Download CSV funciona sem voltar para a primeira aba.
11. Layout é legível em desktop e mobile.
12. `pytest` passa.

---

## 16. Próximos passos sugeridos

1. Finalizar/revisar a alteração local de `data/adapter.py` sobre recuperação e inadimplência de junho.
2. Criar testes para o adapter cobrindo o snapshot atual da query 07/2026.
3. Validar com Carlos os números de:
   - `cupons_milhao`;
   - `cupons_casas`;
   - `recuperacao`;
   - `inad_junho`;
   - `valor_gera_cupom`.
4. Atualizar tooltip/textos do painel quando `valor_recuperado` estiver confirmado como disponível.
5. Decidir e documentar ambiente de produção.
6. Ligar autenticação (`AUTH_ENABLED=true`) somente após configurar OIDC e secrets em ambiente seguro.
7. Definir processo de reconciliação com cupons oficiais quando a plataforma externa disponibilizar os dados.
8. Manter este documento atualizado a cada marco relevante ou mudança de contrato.

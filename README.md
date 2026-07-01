# Painel da Campanha do Milhão

MVP do painel de acompanhamento da **Campanha do Milhão** (Brasil Terrenos).
Streamlit consumindo uma view consolidada no **Microsoft Fabric** (camada de
consumo — nunca o banco operacional do UAU).

> Contexto completo, regras de negócio e pendências: `CONTEXT_PAINEL_DO_MILHAO.md`.

## Arquitetura

```
UAU → consulta/consolidação (Carlos) → Microsoft Fabric → view de consumo → Streamlit (este repo)
```

A ingestão e a view são responsabilidade do time de dados. Este repo **só lê** a view.

## Estrutura

```
app.py                  # visão executiva (entrypoint, single-page com tabs)
components/             # UI: cabeçalho/logo, KPIs, gráficos, formatação BR
data/
  contract.py           # contrato de colunas da view (fonte da verdade)
  onelake.py            # snapshot Parquet do OneLake (service principal Azure AD)
  adapter.py            # bronze → schema interno do painel
  repository.py         # acesso único + cache por janela de atualização (8h/15h BR)
services/
  metrics.py            # regra de cupom + KPIs (único lugar com cálculo financeiro)
  validation.py         # contrato, tipos, duplicidade por venda
config/settings.py      # parâmetros da campanha e regra de cupom (pendências = params)
tests/                  # pytest
```

## Rodar local

```bash
pip install -r requirements.txt
cp .env.example .env          # preencher credenciais Azure (OneLake)
streamlit run app.py
```

## Atualização dos dados

A base do Fabric é atualizada **às 8h e às 15h (horário de Brasília)**. O
painel cacheia por janela: só refaz a query do OneLake quando uma nova janela
começa (com margem de `ATUALIZACAO_MARGEM_MINUTOS`, padrão 20 min → busca às
8h20/15h20, p/ o pipeline terminar de gravar o snapshot). O carimbo "Atualizado" mostra o
horário nominal da base vigente, no fuso BR. A página em modo TV recarrega
sozinha na próxima janela.

## Testes

```bash
pytest
```

## Deploy (Streamlit Community Cloud)

1. Push do repo no GitHub (sem `.env` / `secrets.toml` — já no `.gitignore`).
2. share.streamlit.io → New app → aponta `app.py`.
3. Settings → Secrets: colar o conteúdo de `.streamlit/secrets.toml.example` preenchido.
4. Restringir acesso por e-mail (app privado) em Settings.

`packages.txt` instala deps de sistema (apt) do connector.

## Autenticação (acesso restrito @btsa.com.br)

> **Status: DESLIGADA** (`AUTH_ENABLED=false`, padrão). Painel abre sem login.
> O código do gate está pronto; ligar = passos abaixo.

O painel usa a **auth nativa do Streamlit** (OIDC, `st.login`/`st.user`,
≥ 1.42) com login Google. O gate fica em `services/auth.py:exigir_login_btsa`
e é chamado no topo do `app.py` e de cada arquivo em `pages/` — quando ligado,
sem login com conta **@btsa.com.br** nada é renderizado.

A checagem do domínio é feita **no servidor**, sobre o e-mail já verificado
pelo Google (`email_verified`); o `hd` no `client_kwargs` é só dica de UX.

Para LIGAR:
1. Google Cloud Console → projeto BTSA → OAuth client "Web application".
2. Authorized redirect URI = URL do app + `/oauth2callback`
   (`http://localhost:8501/oauth2callback` local; `https://SEU-APP.streamlit.app/oauth2callback` no Cloud).
3. Preencher a seção `[auth]` em `secrets.toml` (ver `secrets.toml.example`):
   `client_id`, `client_secret`, `cookie_secret` (aleatório), `redirect_uri`.
4. Setar `AUTH_ENABLED=true` (`.env` local **e** Secrets do Community Cloud).
5. (Opcional) Trocar domínio permitido = `DOMINIO_PERMITIDO` em `services/auth.py`.

### ⚠️ Dados sensíveis / LGPD

A base tem CPF, telefone, e-mail e valores. Community Cloud é hosting de
terceiro — subir **dado real** depende de aval do Jurídico (CONTEXT 5.7/8.4).

## Regra de cupom

R$ 100 recebidos = 1 cupom, sobre o valor que entra no caixa, agrupado por
empresa/obra/venda. Componentes (principal/multa/juros/custas) ficam **separados
para auditoria** e controlados por flags em `config/settings.py:RegraCupom`.
A versão da regra (`regra_versao`) é gravada em cada linha calculada.

**Pendências que afetam o cálculo (CONTEXT 13):** tratamento de custas, saldo
residual < R$100, retroatividade ao cadastro, múltiplos compradores. Tratadas
como parâmetros, não como certezas.

## Cupom calculado ≠ cupom oficial

O painel exibe cupons **calculados internamente**. Os **oficiais** vêm da
plataforma externa (coluna `cupons_oficiais`, nula até existir integração).
O painel nunca apresenta número simulado como oficial (CONTEXT 14.3).
```

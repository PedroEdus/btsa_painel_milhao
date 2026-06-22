"""Camada de autenticação do painel.

Usa a autenticação nativa do Streamlit (OIDC, ``st.login``/``st.user``,
disponível a partir do Streamlit 1.42) com o Google como provedor.

Regra de acesso: só entra quem fizer login com uma conta **@btsa.com.br**
(Google Workspace da Brasil Terrenos). Qualquer outro domínio é barrado
*depois* do login do Google — a verificação do domínio é feita no servidor,
sobre o claim de e-mail já validado pelo provedor (``email_verified``),
nunca confiando no que vem do navegador.

A configuração do provedor (client_id/secret, cookie_secret, redirect_uri)
fica em ``.streamlit/secrets.toml`` na seção ``[auth]`` — ver
``secrets.toml.example``.
"""

from __future__ import annotations

import os

import streamlit as st

from config.settings import ALLOWED_EMAIL_DOMAINS, ALLOWED_EMAILS

# Domínios autorizados (lista) + e-mails individuais autorizados. Configuráveis
# via env/secrets (ALLOWED_EMAIL_DOMAINS, ALLOWED_EMAILS) — ver config.settings.
# Fallback ('btsa.com.br',) preserva o comportamento anterior. Sempre minúsculas.
DOMINIOS_PERMITIDOS: tuple[str, ...] = ALLOWED_EMAIL_DOMAINS
EMAILS_PERMITIDOS: tuple[str, ...] = ALLOWED_EMAILS
# Compat: primeiro domínio exibido nas mensagens de login/negação.
DOMINIO_PERMITIDO = DOMINIOS_PERMITIDOS[0] if DOMINIOS_PERMITIDOS else "btsa.com.br"

# Liga/desliga a camada de auth sem mexer no código. Padrão DESLIGADO.
# Para ativar: AUTH_ENABLED=true no .env (local) ou em Secrets (Cloud) +
# preencher a seção [auth] do secrets.toml. Ver README.
AUTH_ENABLED: bool = (os.getenv("AUTH_ENABLED", "false").strip().lower()
                      in {"1", "true", "yes", "sim", "on"})


def _email_autorizado(email: str | None, verificado: bool) -> bool:
    """Decide se o e-mail pode acessar o painel.

    Exige e-mail verificado pelo provedor e pertencente ao domínio da BTSA.
    Comparação por sufixo ``@dominio`` evita falsos positivos como
    ``btsa.com.br.atacante.com``.
    """
    if not email or not verificado:
        return False
    e = email.strip().lower()
    if e in EMAILS_PERMITIDOS:
        return True
    return any(e.endswith("@" + dom) for dom in DOMINIOS_PERMITIDOS)


def _tela_login() -> None:
    """Renderiza a tela de login e interrompe a execução da página."""
    st.markdown(
        """
        <div style="max-width:420px;margin:12vh auto 0;text-align:center;">
          <h1 style="font-size:1.6rem;margin-bottom:.4rem;">Campanha do Milhão</h1>
          <p style="color:#6b7280;margin-bottom:1.6rem;">
            Acesso restrito a colaboradores Brasil Terrenos.<br>
            Entre com sua conta <b>@btsa.com.br</b>.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, meio, _ = st.columns([1, 2, 1])
    with meio:
        if st.button("Entrar com Google", type="primary", use_container_width=True):
            st.login()  # provedor único definido em [auth]
    st.stop()


def _tela_negado(email: str | None) -> None:
    """Usuário logou no Google, mas fora do domínio permitido."""
    st.error(
        f"Acesso negado para **{email or 'esta conta'}**. "
        f"O painel é restrito a contas **@{DOMINIO_PERMITIDO}**."
    )
    if st.button("Sair e tentar com outra conta"):
        st.logout()
    st.stop()


def exigir_login_btsa() -> None:
    """Gate de acesso. Chamar no topo de cada página, antes de qualquer dado.

    - Se não logado: mostra tela de login e para a execução.
    - Se logado fora do domínio @btsa.com.br: nega e para a execução.
    - Se logado e autorizado: retorna e a página segue normalmente.

    Se ``AUTH_ENABLED`` for falso (padrão), o gate é um no-op — painel aberto.
    """
    if not AUTH_ENABLED:
        return

    try:
        logado = bool(st.user.is_logged_in)
    except (AttributeError, KeyError):
        # Seção [auth] ausente em secrets.toml → fail-closed: bloqueia tudo.
        st.error(
            "Autenticação não configurada. Defina a seção `[auth]` em "
            "`.streamlit/secrets.toml` (ver `secrets.toml.example`). "
            "Acesso bloqueado por segurança."
        )
        st.stop()

    if not logado:
        _tela_login()

    email = st.user.get("email")
    verificado = bool(st.user.get("email_verified", False))

    if not _email_autorizado(email, verificado):
        _tela_negado(email)

    _barra_usuario(email)


def _barra_usuario(email: str | None) -> None:
    """Mostra o usuário logado e botão de sair na sidebar."""
    with st.sidebar:
        st.caption(f"Logado como **{email}**")
        if st.button("Sair", use_container_width=True):
            st.logout()

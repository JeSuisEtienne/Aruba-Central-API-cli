"""
Interface Streamlit — Rapport Firmware & Inventaire Aruba Central.

Lancement :
    streamlit run "Script Central/app.py"
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

import streamlit as st

# Résolution des imports locaux (Script Central/)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from pycentral.base import ArubaCentralBase  # noqa: E402

from central_config import charger_central_info, lister_clients  # noqa: E402
from data_pipeline import collect_datasets  # noqa: E402
from excel_export import export_to_excel_buffer  # noqa: E402

# ── Constantes ────────────────────────────────────────────────────────────────
_FEUILLES: tuple[tuple[str, str, str], ...] = (
    ("firmware_consolide", "Firmware Consolidé", "🔄"),
    ("inventaire",         "Inventaire",         "📦"),
    ("switches_stack",     "Switches",           "🔀"),
    ("gateways",           "Gateways",           "🌐"),
    ("firmware_switch",    "Firmware Switch",    "💾"),
    ("firmware_swarms",    "Firmware Swarms",    "📡"),
)


# ── Log handler ───────────────────────────────────────────────────────────────
class _StreamlitLogHandler(logging.Handler):
    """
    Redirige les WARNING/ERROR du logger racine vers l'UI Streamlit.

    Utilisé pour détecter les erreurs d'authentification pycentral qui sont
    loggées plutôt que levées en exception.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.has_errors = False

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if record.levelno >= logging.ERROR:
            self.has_errors = True
            st.error(f"**[{record.name}]** {msg}")
        else:
            st.warning(f"**[{record.name}]** {msg}")


@contextmanager
def _streamlit_log_capture() -> Generator[_StreamlitLogHandler, None, None]:
    """Context manager qui attache/détache le handler Streamlit sur le logger racine."""
    handler = _StreamlitLogHandler()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield handler
    finally:
        root.removeHandler(handler)


# ── Helpers UI ────────────────────────────────────────────────────────────────
def _metric_card(label: str, value: int, icon: str) -> str:
    """Génère le HTML d'une carte métrique."""
    return (
        f'<div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:0.6rem;'
        f' padding:1rem 0.5rem; text-align:center;">'
        f'  <div style="font-size:1.6rem; line-height:1;">{icon}</div>'
        f'  <div style="font-size:1.8rem; font-weight:700; color:#1C2235; margin:0.3rem 0;">{value}</div>'
        f'  <div style="font-size:0.7rem; color:#64748B; text-transform:uppercase;'
        f'       letter-spacing:0.05em;">{label}</div>'
        f'</div>'
    )


def _hero() -> None:
    """Affiche le bandeau d'en-tête stylé."""
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1C2235 0%, #2D3A5E 100%);
            padding: 1.75rem 2rem;
            border-radius: 0.75rem;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            gap: 1.25rem;
        ">
            <span style="font-size:2.75rem; line-height:1;">🔌</span>
            <div>
                <h1 style="color:#FFFFFF; margin:0; font-size:1.65rem; font-weight:700;
                            letter-spacing:-0.01em;">
                    Rapport Firmware &amp; Inventaire
                </h1>
                <p style="color:#94A3B8; margin:0.3rem 0 0; font-size:0.9rem;">
                    Aruba Central — Génération de rapport Excel multi-feuilles
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Aruba Central — Rapports",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Barre latérale ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔌 Aruba Central")
    st.markdown("Outil de reporting réseau multi-clients.")
    st.divider()
    st.markdown("**Navigation**")
    st.page_link("app.py",               label="Firmware & Inventaire", icon="🔌")
    st.page_link("pages/Rapport_MRT.py", label="Rapport MRT",           icon="📊")
    st.divider()
    st.caption("Aruba Central API Tool")

# ── En-tête hero ──────────────────────────────────────────────────────────────
_hero()

# ── Chargement des clients ────────────────────────────────────────────────────
try:
    clients = lister_clients()
except Exception as exc:
    st.error(str(exc))
    st.stop()

# ── Sélection du client ───────────────────────────────────────────────────────
with st.container(border=True):
    col_select, col_btn = st.columns([3, 1], gap="medium")

    with col_select:
        client: str = st.selectbox(
            "Client Aruba Central",
            options=clients,
            help="Sélectionnez le client pour lequel générer le rapport",
        )

    with col_btn:
        st.write("")  # Alignement vertical avec le selectbox
        generer: bool = st.button(
            "▶ Générer",
            type="primary",
            use_container_width=True,
        )

# Réinitialise le cache si le client change
if st.session_state.get("_fw_last_client") != client:
    for key in ("_fw_datasets", "_fw_excel_bytes", "_fw_generated_at"):
        st.session_state.pop(key, None)
    st.session_state["_fw_last_client"] = client

# ── Génération du rapport ─────────────────────────────────────────────────────
if generer:
    with st.status("Génération du rapport en cours…", expanded=True) as status:
        try:
            with _streamlit_log_capture() as log_handler:
                st.write(f"Chargement de la configuration **{client}**…")
                central_info = charger_central_info(client)
                base_url: str = central_info["base_url"]

                token_dir = os.path.join(_SCRIPT_DIR, "temp", client)
                os.makedirs(token_dir, exist_ok=True)
                os.environ["CENTRAL_TOKEN_DIR"] = token_dir

                st.write(f"Connexion à Aruba Central — `{base_url}`")
                central = ArubaCentralBase(
                    central_info=central_info,
                    token_store={"path": token_dir},
                    ssl_verify=True,
                )

                if log_handler.has_errors:
                    raise RuntimeError(
                        "Échec de l'authentification à Aruba Central. "
                        "Vérifiez les identifiants dans auth.env et le fichier .env du client."
                    )

                st.write("Connexion établie. Collecte des données…")
                st.divider()

                datasets = collect_datasets(
                    central=central,
                    base_url=base_url,
                    on_progress=st.write,
                )

                st.divider()
                st.write("Génération du fichier Excel…")
                excel_bytes = export_to_excel_buffer(datasets)

            st.session_state.update({
                "_fw_datasets":     datasets,
                "_fw_excel_bytes":  excel_bytes,
                "_fw_generated_at": datetime.now().strftime("%d/%m/%Y à %H:%M:%S"),
            })
            status.update(label="✅ Rapport généré avec succès !", state="complete")

        except FileNotFoundError as exc:
            status.update(label="Erreur de configuration", state="error")
            st.error(str(exc))
        except ValueError as exc:
            status.update(label="Erreur de configuration", state="error")
            st.error(str(exc))
        except RuntimeError as exc:
            status.update(label="Erreur d'authentification", state="error")
            st.error(str(exc))
            st.info(
                "**Causes fréquentes :**\n"
                "- Identifiants incorrects dans `auth.env` (CENTRAL_USERNAME / CENTRAL_PASSWORD)\n"
                "- CLIENT_ID ou CLIENT_SECRET invalide dans le `.env` du client\n"
                "- Token expiré ou révoqué — supprimez `temp/<client>/` et réessayez"
            )
        except Exception as exc:
            status.update(label="Erreur lors de la génération", state="error")
            st.exception(exc)

# ── Affichage des résultats ───────────────────────────────────────────────────
if "_fw_datasets" in st.session_state:
    datasets: dict     = st.session_state["_fw_datasets"]
    excel_bytes: bytes = st.session_state["_fw_excel_bytes"]
    generated_at: str  = st.session_state.get("_fw_generated_at", "")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        # Métriques
        cols_metrics = st.columns(len(_FEUILLES))
        for col, (key, label, icon) in zip(cols_metrics, _FEUILLES):
            df = datasets.get(key)
            count = len(df) if df is not None and not df.empty else 0
            with col:
                st.markdown(_metric_card(label, count, icon), unsafe_allow_html=True)

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        st.divider()

        # Téléchargement
        col_dl, col_info = st.columns([2, 3], gap="large")
        with col_dl:
            filename = f"{client}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                label="📥 Télécharger le rapport Excel",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
        with col_info:
            if generated_at:
                st.markdown(
                    f"<p style='color:#64748B; font-size:0.85rem; margin:0.6rem 0 0;'>"
                    f"Généré le <strong>{generated_at}</strong> — client <strong>{client}</strong>"
                    f"</p>",
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Aperçu des données
    st.subheader("Aperçu des données")
    tabs = st.tabs([f"{icon} {label}" for _, label, icon in _FEUILLES])
    for tab, (key, label, _) in zip(tabs, _FEUILLES):
        with tab:
            df = datasets.get(key)
            if df is not None and not df.empty:
                st.caption(f"{len(df)} ligne(s) · {len(df.columns)} colonne(s)")
                st.dataframe(df, use_container_width=True, height=420, hide_index=True)
            else:
                st.info(f"Aucune donnée disponible pour « {label} ».")

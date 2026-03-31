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
_FEUILLES: tuple[tuple[str, str], ...] = (
    ("firmware_consolide", "Firmware Consolidé"),
    ("inventaire", "Inventaire"),
    ("switches_stack", "Switches"),
    ("gateways", "Gateways"),
    ("firmware_switch", "Firmware Switch"),
    ("firmware_swarms", "Firmware Swarms"),
)


# ── Capture des logs vers Streamlit ──────────────────────────────────────────
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
    st.page_link("app.py", label="Firmware & Inventaire", icon="🔌")
    st.page_link("pages/Rapport_MRT.py", label="Rapport MRT", icon="📊")
    st.divider()
    st.caption("Aruba Central API Tool")

# ── En-tête ───────────────────────────────────────────────────────────────────
st.title("Rapport Firmware & Inventaire")
st.markdown(
    "Génère un rapport Excel complet : firmware consolidé, inventaire, "
    "switches, gateways et swarms Aruba Central."
)
st.divider()

# ── Chargement des clients ────────────────────────────────────────────────────
try:
    clients = lister_clients()
except Exception as exc:
    st.error(str(exc))
    st.stop()

# ── Sélection du client ───────────────────────────────────────────────────────
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
        "▶ Générer le rapport",
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
                "_fw_datasets": datasets,
                "_fw_excel_bytes": excel_bytes,
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
    datasets: dict = st.session_state["_fw_datasets"]
    excel_bytes: bytes = st.session_state["_fw_excel_bytes"]
    generated_at: str = st.session_state.get("_fw_generated_at", "")

    st.divider()

    # Métriques résumées
    cols_metrics = st.columns(len(_FEUILLES))
    for col, (key, label) in zip(cols_metrics, _FEUILLES):
        df = datasets.get(key)
        col.metric(label, len(df) if df is not None and not df.empty else 0)

    st.write("")

    # Bouton de téléchargement
    col_dl, col_info = st.columns([2, 3], gap="medium")
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
            st.info(f"Rapport généré le **{generated_at}** pour le client **{client}**.")

    st.divider()

    # Aperçu des données par onglet
    st.subheader("Aperçu des données")
    tabs = st.tabs([label for _, label in _FEUILLES])
    for tab, (key, label) in zip(tabs, _FEUILLES):
        with tab:
            df = datasets.get(key)
            if df is not None and not df.empty:
                st.caption(f"{len(df)} ligne(s) · {len(df.columns)} colonne(s)")
                st.dataframe(df, use_container_width=True, height=450, hide_index=True)
            else:
                st.info(f"Aucune donnée disponible pour « {label} ».")

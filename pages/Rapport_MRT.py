"""
Interface Streamlit — Création de Rapports MRT (Monitoring, Reports & Troubleshooting).

Lancement depuis la page principale :
    streamlit run "Script Central/app.py"
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# Résolution des imports locaux (Script Central/)
_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPT_DIR = os.path.abspath(os.path.join(_PAGES_DIR, ".."))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from central_config import charger_central_info, lister_clients  # noqa: E402
from script_mrt_reports import creer_rapport_programme, lister_sites  # noqa: E402

# ── Constantes ────────────────────────────────────────────────────────────────
TYPES_RAPPORTS: Dict[str, str] = {
    "inventory": "Inventory — Liste des équipements",
    "clientInventory": "Client Inventory — Inventaire des clients",
    "clientSession": "Client Session — Sessions clients",
    "appAnalytics": "Application Analytics — Analyses d'applications",
    "deviceUptime": "Device Uptime — Temps de disponibilité des équipements",
    "networkUsage": "Network Usage — Utilisation du réseau",
    "resourceUtilization": "Resource Utilization — Utilisation des ressources",
    "capacityPlanning": "Capacity Planning — Planification de capacité",
    "rfHealth": "RF Health — Santé RF",
    "custom": "Custom — Rapport personnalisé",
}

# Types nécessitant le filtre deviceTypes
TYPES_AVEC_DEVICE_FILTER = {
    "inventory",
    "clientInventory",
    "deviceUptime",
    "networkUsage",
    "resourceUtilization",
    "capacityPlanning",
}

PERIODES = [
    "Dernier jour (LAST_DAY)",
    "Dernière semaine (LAST_WEEK)",
    "Dernier mois (LAST_MONTH)",
    "Plage personnalisée (CUSTOM_RANGE)",
]

SCHEDULES = [
    "Une seule fois (ONE_TIME)",
    "Quotidien (EVERY_DAY)",
    "Hebdomadaire (EVERY_WEEK)",
    "Mensuel (EVERY_MONTH)",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _extraire_code(choix: str) -> str:
    """Extrait le code entre parenthèses d'une option radio (ex: 'Libellé (CODE)' → 'CODE')."""
    return choix.split("(")[1].rstrip(")")


def _build_report_config(
    type_rapport: str,
    report_period: Dict[str, Any],
    report_schedule: Dict[str, Any],
    client_name: str,
    is_global: bool,
    site_ids: Optional[List[str]] = None,
    nom_site: Optional[str] = None,
) -> Dict[str, Any]:
    """Construit le payload JSON pour la création d'un rapport MRT."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{nom_site}" if nom_site else ""
    nom = f"Rapport_{type_rapport}{suffix}_{client_name}_{timestamp}"

    filters: List[Dict[str, Any]] = []
    if is_global:
        filters.append({"filterType": "scope", "values": ["global"]})
    else:
        if not site_ids:
            raise ValueError("site_ids requis pour un rapport par site.")
        filters.append({"filterType": "scope", "values": ["sites"]})
        filters.append({"filterType": "sites", "values": site_ids})

    if type_rapport in TYPES_AVEC_DEVICE_FILTER:
        filters.append({
            "filterType": "deviceTypes",
            "values": ["access_points", "switches", "gateways"],
        })

    return {
        "report": {
            "name": nom,
            "type": type_rapport,
            "timeZone": "Europe/Paris",
            "filters": filters,
            "reportPeriod": report_period,
            "reportSchedule": report_schedule,
        }
    }


# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Aruba Central — Rapport MRT",
    page_icon="📊",
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
st.title("Création de Rapport MRT")
st.markdown(
    "Créez des rapports MRT planifiés via l'API **New Central** (OAuth2). "
    "Le rapport est enregistré directement dans votre interface Aruba Central."
)
st.divider()

# ── Chargement des clients ────────────────────────────────────────────────────
try:
    clients = lister_clients()
except Exception as exc:
    st.error(str(exc))
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 1 — Client
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("1. Client")
client_selectionne: str = st.selectbox(
    "Client Aruba Central",
    options=clients,
    key="mrt_client",
    help="Sélectionnez le client pour lequel créer le rapport MRT",
)

# Réinitialise le cache des sites si le client change
if st.session_state.get("_mrt_last_client") != client_selectionne:
    st.session_state.pop("_mrt_sites", None)
    st.session_state["_mrt_last_client"] = client_selectionne

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 2 — Type de rapport
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("2. Type de rapport")
type_label: str = st.selectbox(
    "Type",
    options=list(TYPES_RAPPORTS.values()),
    key="mrt_type_label",
)
type_rapport: str = next(k for k, v in TYPES_RAPPORTS.items() if v == type_label)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 3 — Période
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("3. Période")
periode_choix: str = st.radio(
    "Période",
    PERIODES,
    horizontal=True,
    key="mrt_periode",
    label_visibility="collapsed",
)

code_periode = _extraire_code(periode_choix)
if code_periode == "CUSTOM_RANGE":
    nb_jours: int = st.number_input(
        "Nombre de jours en arrière",
        min_value=1,
        max_value=365,
        value=7,
        key="mrt_jours",
    )
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=int(nb_jours))
    report_period: Dict[str, Any] = {
        "type": "CUSTOM_RANGE",
        "from": int(start_dt.timestamp()),
        "to": int(end_dt.timestamp()),
    }
    st.caption(
        f"Du **{start_dt.strftime('%d/%m/%Y %H:%M')}** "
        f"au **{end_dt.strftime('%d/%m/%Y %H:%M')}**"
    )
else:
    report_period = {"type": code_periode}

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 4 — Planification
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("4. Planification")
schedule_choix: str = st.radio(
    "Planification",
    SCHEDULES,
    horizontal=True,
    key="mrt_schedule",
    label_visibility="collapsed",
)

code_schedule = _extraire_code(schedule_choix)
if code_schedule == "ONE_TIME":
    report_schedule: Dict[str, Any] = {"recurrenceType": "ONE_TIME"}
else:
    col_sd, col_ed = st.columns(2, gap="medium")
    with col_sd:
        start_d: date = st.date_input("Date de début", value=date.today(), key="mrt_start_date")
    with col_ed:
        end_d: date = st.date_input(
            "Date de fin",
            value=date.today() + timedelta(days=30),
            key="mrt_end_date",
        )
    report_schedule = {
        "recurrenceType": code_schedule,
        "startDate": start_d.strftime("%Y-%m-%d"),
        "endDate": end_d.strftime("%Y-%m-%d"),
    }

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 5 — Périmètre (site)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("5. Périmètre (site)")

SCOPES = [
    "Global — un seul rapport global",
    "Tous les sites — un rapport par site",
    "Site spécifique",
]
scope_choix: str = st.radio(
    "Périmètre",
    SCOPES,
    key="mrt_scope",
    label_visibility="collapsed",
)

sites_a_traiter: Optional[List[Dict[str, str]]] = None
can_create: bool = True


def _charger_sites() -> None:
    """Charge la liste des sites dans session_state."""
    with st.spinner("Récupération des sites depuis l'API…"):
        try:
            info = charger_central_info(client_selectionne)
            st.session_state["_mrt_sites"] = lister_sites(
                base_url=info["base_url"],
                customer_id=info["customer_id"],
                client_id=info["client_id"],
                client_secret=info["client_secret"],
            )
        except Exception as exc:
            st.error(f"Erreur lors du chargement des sites : {exc}")


if "Global" in scope_choix:
    sites_a_traiter = None
    st.info("Un rapport global unique sera créé.")

elif "Tous les sites" in scope_choix:
    if st.button("Charger la liste des sites", key="btn_load_all"):
        _charger_sites()

    if st.session_state.get("_mrt_sites"):
        sites = st.session_state["_mrt_sites"]
        sites_a_traiter = sites
        st.success(f"{len(sites)} site(s) trouvé(s). Un rapport sera créé pour chaque site.")
        with st.expander(f"Voir les {len(sites)} sites"):
            for s in sites:
                st.text(f"• {s['name']}  (id : {s['id']})")
    else:
        st.info("Cliquez sur **Charger la liste des sites** pour continuer.")
        can_create = False

else:  # Site spécifique
    if st.button("Charger la liste des sites", key="btn_load_specific"):
        _charger_sites()

    if st.session_state.get("_mrt_sites"):
        sites = st.session_state["_mrt_sites"]
        site_choisi_nom: str = st.selectbox(
            "Sélectionner un site",
            [s["name"] for s in sites],
            key="mrt_site_choisi",
        )
        site_choisi = next(s for s in sites if s["name"] == site_choisi_nom)
        sites_a_traiter = [site_choisi]
        st.caption(f"ID du site : `{site_choisi['id']}`")
    else:
        st.info("Cliquez sur **Charger la liste des sites** pour sélectionner un site.")
        can_create = False

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 6 — Récapitulatif & création
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("6. Récapitulatif & création")

with st.expander("Voir la configuration complète", expanded=True):
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(f"**Client :** {client_selectionne}")
        st.markdown(f"**Type :** {type_label}")
        st.markdown(f"**Période :** `{report_period.get('type', 'N/A')}`")
    with c2:
        st.markdown(f"**Planification :** `{report_schedule.get('recurrenceType', 'N/A')}`")
        if sites_a_traiter is None:
            st.markdown("**Périmètre :** Global")
        elif len(sites_a_traiter) == 1:
            st.markdown(f"**Périmètre :** Site — *{sites_a_traiter[0]['name']}*")
        else:
            st.markdown(f"**Périmètre :** {len(sites_a_traiter)} sites")

if not can_create:
    st.warning("Complétez la sélection du site pour activer la création.")

creer = st.button(
    "▶ Créer le(s) rapport(s)",
    type="primary",
    disabled=not can_create,
    use_container_width=True,
)

# ── Logique de création ───────────────────────────────────────────────────────
if creer:
    try:
        info = charger_central_info(client_selectionne)
        base_url: str = info["base_url"]
        customer_id: str = info["customer_id"]
        client_id: str = info["client_id"]
        client_secret: str = info["client_secret"]

        def _creer(config: Dict[str, Any]) -> Dict[str, Any]:
            return creer_rapport_programme(
                base_url=base_url,
                customer_id=customer_id,
                client_id=client_id,
                client_secret=client_secret,
                rapport_config=config,
            )

        # ── CAS 1 : Global ────────────────────────────────────────────────────
        if sites_a_traiter is None:
            with st.status("Création du rapport global…", expanded=True) as status:
                st.write("Envoi de la requête à l'API New Central…")
                result = _creer(_build_report_config(
                    type_rapport, report_period, report_schedule,
                    client_selectionne, is_global=True,
                ))
                status.update(label="✅ Rapport global créé !", state="complete")
            st.success("Rapport global créé avec succès !")
            if result:
                st.json(result)

        # ── CAS 2 : Site spécifique ───────────────────────────────────────────
        elif len(sites_a_traiter) == 1:
            site = sites_a_traiter[0]
            with st.status(f"Création du rapport pour **{site['name']}**…", expanded=True) as status:
                st.write("Envoi de la requête à l'API New Central…")
                result = _creer(_build_report_config(
                    type_rapport, report_period, report_schedule,
                    client_selectionne, is_global=False,
                    site_ids=[site["id"]], nom_site=site["name"],
                ))
                status.update(label=f"✅ Rapport créé pour {site['name']} !", state="complete")
            st.success(f"Rapport créé pour **{site['name']}** !")
            if result:
                st.json(result)

        # ── CAS 3 : Tous les sites ────────────────────────────────────────────
        else:
            nb = len(sites_a_traiter)
            progress_bar = st.progress(0, text=f"0 / {nb} rapports créés…")
            results_ok: List[Dict[str, str]] = []
            results_err: List[Dict[str, str]] = []

            for i, site in enumerate(sites_a_traiter, 1):
                try:
                    r = _creer(_build_report_config(
                        type_rapport, report_period, report_schedule,
                        client_selectionne, is_global=False,
                        site_ids=[site["id"]], nom_site=site["name"],
                    ))
                    results_ok.append({
                        "Site": site["name"],
                        "ID rapport": r.get("id", "N/A"),
                        "Nom": r.get("name", "N/A"),
                    })
                except Exception as exc:
                    results_err.append({"Site": site["name"], "Erreur": str(exc)})
                progress_bar.progress(i / nb, text=f"{i} / {nb} rapports traités…")

            progress_bar.empty()

            col_ok, col_err = st.columns(2)
            col_ok.metric("Rapports créés", len(results_ok))
            col_err.metric("Erreurs", len(results_err))

            if results_ok:
                with st.expander(f"✅ {len(results_ok)} rapport(s) créé(s) avec succès", expanded=True):
                    st.dataframe(pd.DataFrame(results_ok), use_container_width=True, hide_index=True)

            if results_err:
                with st.expander(f"❌ {len(results_err)} erreur(s)", expanded=True):
                    st.dataframe(pd.DataFrame(results_err), use_container_width=True, hide_index=True)

    except Exception as exc:
        st.exception(exc)

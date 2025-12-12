"""
Module pour récupérer les informations de firmware des swarms (groupes d'AP) via l'API Aruba Central.

Ce module utilise l'endpoint `firmware/v1/swarms` pour récupérer la liste des swarms
et expose trois DataFrames :
    - un tableau détaillé (une ligne par VC / swarm)
    - un tableau par point d'accès
    - un tableau synthétique (VC, version actuelle, version recommandée)
"""

from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests

from script_load_token import load_token, get_access_token


def _vc_row_from_swarm(swarm: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme un objet swarm en une ligne représentant le Virtual Controller.
    """
    aps = swarm.get("aps") or []
    status = swarm.get("status") or {}
    ap_reference = aps[0] if aps else {}

    return {
        "serial": swarm.get("swarm_id"),
        "mac_address": ap_reference.get("mac_address"),
        "hostname": swarm.get("swarm_name"),
        "model": ap_reference.get("model"),
        "vc_name": swarm.get("swarm_name"),
        "vc_id": swarm.get("swarm_id"),
        "members_count": len(aps),
        "firmware_version": swarm.get("firmware_version"),
        "recommended": swarm.get("recommended"),
        "device_status": swarm.get("device_status"),
        "upgrade_required": swarm.get("upgrade_required"),
        "status_state": status.get("state"),
        "status_reason": status.get("reason"),
        "firmware_scheduled_at": status.get("firmware_scheduled_at"),
    }


def _ap_rows_from_swarm(swarm: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transforme un objet swarm en plusieurs lignes représentant chaque AP du swarm.
    """
    aps = swarm.get("aps") or []
    status = swarm.get("status") or {}
    rows: List[Dict[str, Any]] = []
    for ap in aps:
        rows.append(
            {
                "serial": ap.get("serial"),
                "mac_address": ap.get("mac_address"),
                "hostname": ap.get("name"),
                "model": ap.get("model"),
                "vc_name": swarm.get("swarm_name"),
                "vc_id": swarm.get("swarm_id"),
                "firmware_version": swarm.get("firmware_version"),
                "recommended": swarm.get("recommended"),
                "device_status": swarm.get("device_status"),
                "upgrade_required": swarm.get("upgrade_required"),
                "status_state": status.get("state"),
                "status_reason": status.get("reason"),
                "firmware_scheduled_at": status.get("firmware_scheduled_at"),
            }
        )
    return rows


def get_firmware_swarms(
    limit: Optional[int] = None,
    base_url: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Récupère la liste des swarms et retourne :
        - un DataFrame détaillé (une ligne par VC)
        - un DataFrame synthétique (VC, version actuelle, version recommandée)

    Parameters
    ----------
    limit : Optional[int]
        Nombre maximum de swarms à retourner (paramètre `limit` de l'API).

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        (df_details_vc, df_aps, df_versions_vc)
    """
    token_payload = load_token()
    access_token = get_access_token(token_payload)

    if not base_url:
        raise ValueError("La base URL Aruba Central doit être fournie pour les swarms.")
    endpoint = base_url.rstrip("/") + "/firmware/v1/swarms"
    print(f"🔗 Appel API swarms : {endpoint}")
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
    }
    params = {}
    if limit is not None:
        params["limit"] = limit

    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur {response.status_code}: {response.text}")

    data = response.json()
    swarms = data.get("swarms", [])

    details_rows: List[Dict[str, Any]] = []
    aps_rows: List[Dict[str, Any]] = []
    versions_rows: List[Dict[str, Any]] = []
    for swarm in swarms:
        details_rows.append(_vc_row_from_swarm(swarm))
        aps_rows.extend(_ap_rows_from_swarm(swarm))
        versions_rows.append(
            {
                "vc_name": swarm.get("swarm_name"),
                "firmware_version": swarm.get("firmware_version"),
                "recommended_firmware_version": swarm.get("recommended"),
            }
        )

    if not details_rows and not aps_rows:
        empty_details = pd.DataFrame(
            columns=[
                "serial",
                "mac_address",
                "hostname",
                "model",
                "vc_name",
                "vc_id",
                "members_count",
                "firmware_version",
                "recommended",
                "device_status",
                "upgrade_required",
                "status_state",
                "status_reason",
                "firmware_scheduled_at",
            ]
        )

        empty_aps = pd.DataFrame(
            columns=[
                "serial",
                "mac_address",
                "hostname",
                "model",
                "vc_name",
                "vc_id",
                "firmware_version",
                "recommended",
                "device_status",
                "upgrade_required",
                "status_state",
                "status_reason",
                "firmware_scheduled_at",
            ]
        )

        empty_versions = pd.DataFrame(
            columns=["vc_name", "firmware_version", "recommended_firmware_version"]
        )
        return empty_details, empty_aps, empty_versions

    df_details = pd.DataFrame(details_rows) if details_rows else pd.DataFrame()
    df_aps = pd.DataFrame(aps_rows) if aps_rows else pd.DataFrame()
    df_versions = pd.DataFrame(versions_rows).drop_duplicates()

    # Harmoniser visuellement les booléens pour Excel
    for df in (df_details, df_aps):
        if not df.empty and "upgrade_required" in df.columns:
            df["upgrade_required"] = df["upgrade_required"].apply(
                lambda x: "Yes" if bool(x) else "No"
            )

    return df_details, df_aps, df_versions


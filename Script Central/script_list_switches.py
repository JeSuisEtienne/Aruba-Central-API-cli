"""
Module pour lister les switches via l'API monitoring/v1/switches et marquer
ceux qui appartiennent à un stack.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from script_load_token import get_access_token, load_token


def _recuperer_page_switches(
    base_url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Récupère une page de switches et retourne la liste brute."""
    endpoint = base_url.rstrip("/") + "/monitoring/v1/switches"
    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur {response.status_code}: {response.text}")

    payload = response.json() if response.text else {}
    switches = payload.get("switches") or payload.get("data") or []
    return switches


def lister_switches_stack(
    base_url: str,
    group: Optional[str] = None,
    label: Optional[str] = None,
    stack_id: Optional[str] = None,
    limit: int = 100,
) -> pd.DataFrame:
    """
    Liste les switches et indique s'ils font partie d'un stack.

    Parameters
    ----------
    base_url : str
        URL de base Aruba Central (ex: https://apigw-prod2.central.arubanetworks.com)
    group : Optional[str]
        Filtre sur un groupe (group ou label ou stack_id sont exclusifs côté API)
    label : Optional[str]
        Filtre sur un label
    stack_id : Optional[str]
        Filtre sur un stack précis
    limit : int
        Nombre d'entrées par page (pagination)
    """
    if not base_url:
        raise ValueError("La base URL Aruba Central doit être fournie pour lister les switches.")

    token_payload = load_token()
    access_token = get_access_token(token_payload)

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
    }

    params_base: Dict[str, Any] = {"limit": limit}
    if group:
        params_base["group"] = group
    if label:
        params_base["label"] = label
    if stack_id:
        params_base["stack_id"] = stack_id

    offset = 0
    tous_switches: List[Dict[str, Any]] = []

    while True:
        params = {**params_base, "offset": offset}
        switches = _recuperer_page_switches(base_url=base_url, headers=headers, params=params)
        if not switches:
            break

        tous_switches.extend(switches)
        if len(switches) < limit:
            break
        offset += limit

    if not tous_switches:
        return pd.DataFrame()

    df = pd.json_normalize(tous_switches)

    # Colonnes stack -> on essaie de récupérer les différentes variantes possibles
    if "stack_id" not in df.columns:
        df["stack_id"] = df.get("stack_info.stack_id")
    if "stack_role" not in df.columns:
        df["stack_role"] = df.get("stack_info.role")
    if "stack_member_id" not in df.columns:
        df["stack_member_id"] = df.get("stack_info.member_id")

    df["stack_status"] = df["stack_id"].apply(
        lambda sid: "Stack" if pd.notna(sid) and str(sid).strip() not in ("", "0") else "Standalone"
    )

    columns_order = [
        "serial",
        "macaddr",
        "name",
        "ip_address",
        "model",
        "status",
        "group_name",
        "site",
        "stack_status",
        "stack_id",
        "stack_role",
        "stack_member_id",
    ]

    for col in columns_order:
        if col not in df.columns:
            df[col] = None

    df = df[columns_order]
    return df


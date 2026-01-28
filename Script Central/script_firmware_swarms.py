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


def _recuperer_aps_monitoring(base_url: str) -> pd.DataFrame:
    """
    Récupère la liste des APs depuis l'API monitoring/v2/aps pour obtenir les champs 'site' et 'ip_address'.
    
    Parameters
    ----------
    base_url : str
        URL de base Aruba Central
        
    Returns
    -------
    pd.DataFrame
        DataFrame contenant serial, macaddr, site et ip_address pour chaque AP
    """
    token_payload = load_token()
    access_token = get_access_token(token_payload)
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
    }
    
    endpoint = base_url.rstrip("/") + "/monitoring/v2/aps"
    print(f"🔗 Appel API monitoring/v2/aps pour récupérer les sites et adresses IP...")
    
    offset = 0
    limit = 100
    tous_aps: List[Dict[str, Any]] = []
    
    while True:
        params = {"limit": limit, "offset": offset}
        response = requests.get(endpoint, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"⚠️ Erreur {response.status_code} lors de la récupération des APs: {response.text[:200]}")
            break
        
        payload = response.json() if response.text else {}
        aps = payload.get("aps") or payload.get("data") or []
        
        if not aps:
            break
        
        tous_aps.extend(aps)
        if len(aps) < limit:
            break
        offset += limit
    
    if not tous_aps:
        return pd.DataFrame(columns=["serial", "macaddr", "site", "ip_address"])
    
    # Créer un DataFrame avec serial, macaddr, site et ip_address
    aps_data = []
    for ap in tous_aps:
        aps_data.append({
            "serial": ap.get("serial"),
            "macaddr": ap.get("macaddr"),
            "site": ap.get("site"),
            "ip_address": ap.get("ip_address"),
        })
    
    return pd.DataFrame(aps_data)


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


def _enrichir_aps_avec_site(df_aps: pd.DataFrame, base_url: str) -> pd.DataFrame:
    """
    Enrichit le DataFrame des APs avec les champs 'site' et 'ip_address' depuis l'API monitoring/v2/aps.
    
    Parameters
    ----------
    df_aps : pd.DataFrame
        DataFrame contenant les APs des swarms
    base_url : str
        URL de base Aruba Central
        
    Returns
    -------
    pd.DataFrame
        DataFrame enrichi avec les colonnes 'site' et 'ip_address'
    """
    if df_aps is None or df_aps.empty:
        if df_aps is not None:
            df_aps = df_aps.copy()
            df_aps["site"] = None
            df_aps["ip_address"] = None
        return df_aps
    
    if "serial" not in df_aps.columns:
        print("⚠️ Colonne 'serial' absente, impossible d'enrichir avec le site et l'IP")
        df_aps = df_aps.copy()
        df_aps["site"] = None
        df_aps["ip_address"] = None
        return df_aps
    
    # Récupérer les APs depuis l'API monitoring
    try:
        df_aps_monitoring = _recuperer_aps_monitoring(base_url)
        
        if df_aps_monitoring.empty:
            print("⚠️ Aucun AP trouvé dans l'API monitoring, site et IP seront vides")
            df_aps = df_aps.copy()
            df_aps["site"] = None
            df_aps["ip_address"] = None
            return df_aps
        
        # Créer une copie pour éviter les warnings
        df_aps = df_aps.copy()
        
        # Créer des dictionnaires de mapping serial -> site et ip_address
        site_map_serial = dict(zip(df_aps_monitoring["serial"], df_aps_monitoring["site"]))
        ip_map_serial = dict(zip(df_aps_monitoring["serial"], df_aps_monitoring["ip_address"]))
        
        # Créer des dictionnaires de mapping macaddr -> site et ip_address (en cas d'échec avec serial)
        # Normaliser mac_address pour la comparaison
        df_aps_monitoring["macaddr_normalized"] = (
            df_aps_monitoring["macaddr"]
            .astype(str)
            .str.replace(":", "")
            .str.replace("-", "")
            .str.upper()
        )
        site_map_mac = dict(zip(df_aps_monitoring["macaddr_normalized"], df_aps_monitoring["site"]))
        ip_map_mac = dict(zip(df_aps_monitoring["macaddr_normalized"], df_aps_monitoring["ip_address"]))
        
        # Appliquer le mapping sur serial d'abord
        df_aps["site"] = df_aps["serial"].map(site_map_serial)
        df_aps["ip_address"] = df_aps["serial"].map(ip_map_serial)
        
        # Pour les APs sans site ou IP, essayer avec mac_address
        mask_sans_donnees = df_aps["site"].isna() | df_aps["ip_address"].isna()
        if mask_sans_donnees.any() and "mac_address" in df_aps.columns:
            df_aps.loc[mask_sans_donnees, "mac_address_normalized"] = (
                df_aps.loc[mask_sans_donnees, "mac_address"]
                .astype(str)
                .str.replace(":", "")
                .str.replace("-", "")
                .str.upper()
            )
            # Mettre à jour le site si manquant
            mask_site_manquant = df_aps["site"].isna()
            if mask_site_manquant.any():
                df_aps.loc[mask_site_manquant, "site"] = (
                    df_aps.loc[mask_site_manquant, "mac_address_normalized"].map(site_map_mac)
                )
            # Mettre à jour l'IP si manquante
            mask_ip_manquante = df_aps["ip_address"].isna()
            if mask_ip_manquante.any():
                df_aps.loc[mask_ip_manquante, "ip_address"] = (
                    df_aps.loc[mask_ip_manquante, "mac_address_normalized"].map(ip_map_mac)
                )
            # Supprimer la colonne temporaire
            df_aps = df_aps.drop(columns=["mac_address_normalized"], errors="ignore")
        
        print(f"✅ Sites récupérés pour {df_aps['site'].notna().sum()}/{len(df_aps)} AP(s)")
        print(f"✅ Adresses IP récupérées pour {df_aps['ip_address'].notna().sum()}/{len(df_aps)} AP(s)")
        
    except Exception as err:
        print(f"⚠️ Erreur lors de la récupération des sites et IPs: {err}")
        df_aps = df_aps.copy()
        df_aps["site"] = None
        df_aps["ip_address"] = None
    
    return df_aps


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
                "site",
                "ip_address",
            ]
        )

        empty_versions = pd.DataFrame(
            columns=["vc_name", "firmware_version", "recommended_firmware_version"]
        )
        return empty_details, empty_aps, empty_versions

    df_details = pd.DataFrame(details_rows) if details_rows else pd.DataFrame()
    df_aps = pd.DataFrame(aps_rows) if aps_rows else pd.DataFrame()
    df_versions = pd.DataFrame(versions_rows).drop_duplicates()

    # Enrichir les APs avec les champs site et ip_address depuis l'API monitoring/v2/aps
    if not df_aps.empty and base_url:
        df_aps = _enrichir_aps_avec_site(df_aps, base_url)
    elif not df_aps.empty:
        df_aps["site"] = None
        df_aps["ip_address"] = None

    # Harmoniser visuellement les booléens pour Excel
    for df in (df_details, df_aps):
        if not df.empty and "upgrade_required" in df.columns:
            df["upgrade_required"] = df["upgrade_required"].apply(
                lambda x: "Yes" if bool(x) else "No"
            )

    return df_details, df_aps, df_versions


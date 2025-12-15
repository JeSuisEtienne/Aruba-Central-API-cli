"""
Pipeline de collecte et de transformation des données depuis Aruba Central.

Ce module regroupe l'ensemble de la logique métier nécessaire pour
préparer les jeux de données utilisés dans le rapport Excel.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd
from pycentral.classic.base import ArubaCentralBase

from script_inventaire import recuperer_inventaire
from script_firmware_switch import get_firmware_switch
from script_firmware_swarms import get_firmware_swarms
from script_firmware_versions import get_firmware_versions, max_version_same_branch, max_version_same_branch_gateway
from script_list_switches import lister_switches_stack
from script_list_gateways import lister_gateways, enrichir_gateways_recommended


DataFramesMap = Dict[str, pd.DataFrame]

CONSOLIDE_COLONNES = [
    "serial",
    "mac_address",
    "hostname",
    "model",
    "firmware_version",
    "recommended",
    "firmware_max",
]


def _concat_frames(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatène une liste de DataFrame non vides."""
    frames_valides = [df for df in frames if df is not None and not df.empty]
    if not frames_valides:
        return pd.DataFrame()
    return pd.concat(frames_valides, ignore_index=True)


def _calculer_firmware_max_switches(
    df_switches: pd.DataFrame,
    base_url: str,
) -> pd.DataFrame:
    """
    Calcule la meilleure version de firmware disponible pour chaque switch en
    se basant sur la même branche et selon le modèle (2930F / 6300).
    """
    if df_switches.empty:
        df_switches["firmware_max"] = None
        return df_switches

    modele_series = df_switches["model"].fillna("").str.upper()

    versions_hp: Optional[List[str]] = None
    versions_cx: Optional[List[str]] = None

    if (modele_series.str.contains("2930F")).any():
        try:
            versions_hp = get_firmware_versions(device_type="HP", base_url=base_url)
        except Exception as err:  # pragma: no cover - log utilisateur
            print("⚠️ Impossible de récupérer les versions HP :", err)

    if (modele_series.str.contains("6300")).any():
        try:
            versions_cx = get_firmware_versions(device_type="CX", base_url=base_url)
        except Exception as err:  # pragma: no cover - log utilisateur
            print("⚠️ Impossible de récupérer les versions CX :", err)

    def determiner_version_max(modele: str, version_actuelle: Optional[str]) -> Optional[str]:
        if not version_actuelle:
            return None

        modele_upper = (modele or "").upper()
        base_versions: Optional[List[str]] = None

        if versions_hp and "2930F" in modele_upper:
            base_versions = versions_hp
        elif versions_cx and ("6300" in modele_upper or "CX" in modele_upper):
            base_versions = versions_cx

        if not base_versions:
            return None

        return max_version_same_branch(version_actuelle, base_versions)

    df_switches["firmware_max"] = df_switches.apply(
        lambda row: determiner_version_max(row.get("model"), row.get("firmware_version")),
        axis=1,
    )

    return df_switches


def _calculer_firmware_max_swarms(
    df_vc: pd.DataFrame,
    df_aps: pd.DataFrame,
    df_vc_versions: pd.DataFrame,
    base_url: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ajoute la colonne firmware_max pour les swarms (VC + AP) et éventuellement la vue versions."""
    if df_vc.empty and df_aps.empty:
        for df in (df_vc, df_aps, df_vc_versions):
            df["firmware_max"] = None
        return df_vc, df_aps, df_vc_versions

    versions_iap: Optional[List[str]] = None
    try:
        versions_iap = get_firmware_versions(device_type="IAP", base_url=base_url)
    except Exception as err:  # pragma: no cover - log utilisateur
        print("⚠️ Impossible de récupérer les versions IAP :", err)

    def appliquer(df: pd.DataFrame) -> None:
        if df.empty:
            df["firmware_max"] = None
        elif versions_iap:
            df["firmware_max"] = df["firmware_version"].apply(
                lambda current: max_version_same_branch(current, versions_iap)
            )
        else:
            df["firmware_max"] = None

    appliquer(df_vc)
    appliquer(df_aps)
    appliquer(df_vc_versions)

    return df_vc, df_aps, df_vc_versions


def _calculer_firmware_max_gateways(
    df_gateways: pd.DataFrame,
    base_url: str,
) -> pd.DataFrame:
    """
    Ajoute firmware_max pour les gateways en restant dans la même branche.
    """
    if df_gateways is None or df_gateways.empty:
        return df_gateways

    # S'assurer que la colonne firmware_version existe
    if "firmware_version" not in df_gateways.columns:
        df_gateways["firmware_version"] = None

    versions_gw: Optional[List[str]] = None
    try:
        # Les gateways sont exposés sous le type "CONTROLLER".
        versions_gw = get_firmware_versions(device_type="CONTROLLER", base_url=base_url)
    except Exception as err:  # pragma: no cover - log utilisateur
        print("⚠️ Impossible de récupérer les versions Gateway :", err)

    if versions_gw:
        def calculer_max(current: Optional[str]) -> Optional[str]:
            if not current or pd.isna(current):
                return None
            # Utiliser la fonction spécialisée pour les gateways qui gère le format "8.7.0.0-2.3.0.9_85196"
            return max_version_same_branch_gateway(str(current), versions_gw)

        df_gateways["firmware_max"] = df_gateways["firmware_version"].apply(calculer_max)
    else:
        print("⚠️ Aucune version CONTROLLER disponible, firmware_max sera vide")
        df_gateways["firmware_max"] = None

    # S'assurer que la colonne firmware_max existe même si elle n'a pas été créée
    if "firmware_max" not in df_gateways.columns:
        df_gateways["firmware_max"] = None

    return df_gateways


def _preparer_gateways_consolide(df_gateways: pd.DataFrame) -> pd.DataFrame:
    """
    Aligne les colonnes des gateways sur la vue consolidée firmware.
    """
    if df_gateways is None or df_gateways.empty:
        return pd.DataFrame(columns=CONSOLIDE_COLONNES)

    df = df_gateways.rename(columns={"macaddr": "mac_address", "name": "hostname"}).copy()

    # S'assurer que toutes les colonnes requises existent
    for col in CONSOLIDE_COLONNES:
        if col not in df.columns:
            df[col] = None

    # Sélectionner uniquement les colonnes consolidées (firmware_max devrait être préservé)
    df_result = df[CONSOLIDE_COLONNES].copy()

    return df_result


def collect_datasets(central: ArubaCentralBase, base_url: str) -> DataFramesMap:
    """
    Collecte l'ensemble des jeux de données nécessaires au rapport.

    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionnaire contenant les DataFrame prêts à être exportés.
    """
    df_inventory = recuperer_inventaire(conn=central)
    df_switches_stack = lister_switches_stack(base_url=base_url)
    df_gateways = lister_gateways(base_url=base_url)
    df_gateways = enrichir_gateways_recommended(df_gateways, base_url=base_url)
    df_gateways = _calculer_firmware_max_gateways(df_gateways, base_url=base_url)

    df_switch_hp = get_firmware_switch(
        conn=central,
        device_type="HP",
        limit=500,
        base_url=base_url,
    )
    df_switch_cx = get_firmware_switch(
        conn=central,
        device_type="CX",
        limit=500,
        base_url=base_url,
    )
    df_switch = _concat_frames([df_switch_hp, df_switch_cx])
    df_switch = _calculer_firmware_max_switches(df_switch, base_url=base_url)

    df_swarms_vc, df_swarms_ap, df_vc_versions = get_firmware_swarms(base_url=base_url)
    df_swarms_vc, df_swarms_ap, df_vc_versions = _calculer_firmware_max_swarms(
        df_swarms_vc,
        df_swarms_ap,
        df_vc_versions,
        base_url=base_url,
    )

    df_gateways_consolide = _preparer_gateways_consolide(df_gateways)

    # Consolidation : switches, VC et gateways (pas les APs individuels)
    df_consolide = _concat_frames(
        [
            df_switch.reindex(columns=CONSOLIDE_COLONNES, copy=False)
            if not df_switch.empty
            else None,
            df_swarms_vc.reindex(columns=CONSOLIDE_COLONNES, copy=False)
            if not df_swarms_vc.empty
            else None,
            df_gateways_consolide if not df_gateways_consolide.empty else None,
        ]
    )

    # Prépare un tableau combinant VC et AP pour l'onglet Firmware Swarms
    df_swarms_sheet = _concat_frames(
        [
            df_swarms_vc.assign(type_entree="VC") if not df_swarms_vc.empty else None,
            df_swarms_ap.assign(type_entree="AP") if not df_swarms_ap.empty else None,
        ]
    )
    if not df_swarms_sheet.empty:
        # Place type_entree en première colonne pour la lisibilité
        cols = ["type_entree"] + [col for col in df_swarms_sheet.columns if col != "type_entree"]
        df_swarms_sheet = df_swarms_sheet[cols]

    return {
        "inventaire": df_inventory,
        "switches_stack": df_switches_stack,
        "gateways": df_gateways,
        "firmware_switch": df_switch,
        "firmware_swarms": df_swarms_sheet,
        "firmware_consolide": df_consolide,
    }


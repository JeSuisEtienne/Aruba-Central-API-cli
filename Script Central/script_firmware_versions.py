"""
Utilitaires pour récupérer et filtrer les versions de firmware depuis Aruba Central.
"""

import re
from typing import List, Optional, Tuple

import requests

from script_load_token import load_token, get_access_token


def _version_to_tuple(version: str, length: int = 4) -> Optional[Tuple[int, ...]]:
    """
    Convertit une version au format chaîne en tuple d'entiers comparable.
    Exemple : "8.13.0.0" -> (8, 13, 0, 0)
    """
    if not version:
        return None

    numbers = re.findall(r"\d+", version)
    if not numbers:
        return None

    values = [int(num) for num in numbers[:length]]
    while len(values) < length:
        values.append(0)
    return tuple(values)


def get_firmware_versions(device_type: str = "IAP", base_url: Optional[str] = None) -> List[str]:
    """
    Récupère la liste des versions disponibles pour un type d'équipement donné.
    """
    token_payload = load_token()
    access_token = get_access_token(token_payload)

    if not base_url:
        raise ValueError("La base URL Aruba Central doit être fournie pour les versions firmware.")

    endpoint = base_url.rstrip("/") + "/firmware/v1/versions"
    print(f"🔗 Appel API versions ({device_type}) : {endpoint}")
    params = {"device_type": device_type}
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
    }

    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur {response.status_code}: {response.text}")

    try:
        payload = response.json()
    except ValueError as err:
        raise ValueError(f"❌ Réponse JSON invalide : {err}") from err

    if isinstance(payload, dict):
        versions_raw = payload.get("data") or payload.get("versions") or []
    elif isinstance(payload, list):
        versions_raw = payload
    else:
        versions_raw = []

    versions: List[str] = []
    for entry in versions_raw:
        if isinstance(entry, dict):
            firmware_version = entry.get("firmware_version")
            if firmware_version:
                versions.append(str(firmware_version))
        elif isinstance(entry, str):
            versions.append(entry)

    # Suppression des doublons tout en conservant l'ordre
    seen = set()
    unique_versions = []
    for version in versions:
        if version not in seen:
            seen.add(version)
            unique_versions.append(version)

    return unique_versions


def filter_versions_same_branch_higher(
    current_version: str, versions: List[str]
) -> List[str]:
    """
    Filtre les versions strictement supérieures à current_version
    tout en restant dans la même branche (deux premiers segments).
    """
    current_tuple = _version_to_tuple(current_version)
    if not current_tuple:
        return []

    branch = current_tuple[:2]
    filtered: List[str] = []

    for version in versions:
        candidate_tuple = _version_to_tuple(version)
        if not candidate_tuple:
            continue
        if candidate_tuple[:2] != branch:
            continue
        if candidate_tuple > current_tuple:
            filtered.append(version)

    filtered.sort(key=lambda v: _version_to_tuple(v) or (0, 0, 0, 0))
    return filtered


def max_version_same_branch(current_version: str, versions: List[str]) -> Optional[str]:
    """
    Retourne la version maximale disponible dans la même branche que current_version.
    """
    filtered = filter_versions_same_branch_higher(current_version, versions)
    if not filtered:
        return None
    return filtered[-1]


def _extract_main_version(version: str) -> str:
    """
    Extrait la partie principale d'une version gateway (avant le tiret).
    Exemple : "8.7.0.0-2.3.0.9_85196" -> "8.7.0.0"
    """
    if not version:
        return ""
    # Prendre la partie avant le premier tiret
    parts = version.split("-", 1)
    return parts[0] if parts else version


def _gateway_version_to_tuple(version: str) -> Optional[Tuple[int, ...]]:
    """
    Convertit une version gateway complète en tuple pour comparaison.
    Exemple : "8.7.0.0-2.3.0.9" -> (8, 7, 0, 0, 2, 3, 0, 9)
    """
    if not version:
        return None

    # Séparer la partie principale et la partie secondaire
    parts = version.split("-", 1)
    main_part = parts[0] if parts else version
    secondary_part = parts[1] if len(parts) > 1 else ""

    # Extraire les nombres de la partie principale
    main_numbers = re.findall(r"\d+", main_part)
    main_values = [int(num) for num in main_numbers[:4]]  # Limiter à 4 segments
    while len(main_values) < 4:
        main_values.append(0)

    # Extraire les nombres de la partie secondaire (avant le underscore si présent)
    secondary_clean = secondary_part.split("_")[0] if secondary_part else ""
    secondary_numbers = re.findall(r"\d+", secondary_clean)
    secondary_values = [int(num) for num in secondary_numbers[:4]]  # Limiter à 4 segments
    while len(secondary_values) < 4:
        secondary_values.append(0)

    # Combiner les deux parties
    return tuple(main_values + secondary_values)


def max_version_same_branch_gateway(current_version: str, versions: List[str]) -> Optional[str]:
    """
    Retourne la version maximale disponible dans la même branche pour les gateways.
    Gère le format spécial des gateways : "8.7.0.0-2.3.0.9_85196"
    Compare la version complète (partie principale + partie secondaire).
    Si la version actuelle est la plus récente, elle est retournée.
    """
    if not current_version or not versions:
        return None

    # Convertir la version actuelle en tuple complet
    current_tuple_full = _gateway_version_to_tuple(current_version)
    if not current_tuple_full:
        return None

    # La branche est définie par les deux premiers segments de la partie principale
    branch = current_tuple_full[:2]  # Branche = deux premiers segments (ex: 8.7)
    candidates: List[Tuple[Tuple[int, ...], str]] = []

    # Vérifier si la version actuelle est dans la liste des versions disponibles
    current_in_list = current_version in versions

    for version in versions:
        # Convertir chaque version candidate en tuple complet
        candidate_tuple_full = _gateway_version_to_tuple(version)
        if not candidate_tuple_full:
            continue

        # Vérifier que c'est dans la même branche (même partie principale 8.7.x.x)
        if candidate_tuple_full[:2] != branch:
            continue

        # Garder la version complète avec son tuple complet pour comparaison
        candidates.append((candidate_tuple_full, version))

    # Si la version actuelle n'est pas dans la liste mais qu'on a des candidats dans la branche,
    # on peut quand même la considérer pour comparaison
    if not current_in_list and current_tuple_full[:2] == branch:
        candidates.append((current_tuple_full, current_version))

    if not candidates:
        return None

    # Trier par tuple complet et retourner la version complète maximale
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]
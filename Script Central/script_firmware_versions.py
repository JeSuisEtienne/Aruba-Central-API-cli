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


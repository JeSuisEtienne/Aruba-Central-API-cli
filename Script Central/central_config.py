"""
Module de configuration pour la connexion à Aruba Central.

Ce module se charge de récupérer les informations de connexion
pour un client donné à partir d'un fichier .env spécifique.
Les identifiants (username/password) sont chargés depuis le fichier auth.env principal.
"""

from typing import Dict, List
import os
from pathlib import Path

from dotenv import dotenv_values

from clients_config import CLIENTS


# Chemin vers le fichier auth.env principal contenant les identifiants
ENV_PRINCIPAL = Path(__file__).resolve().parent / "auth.env"


def charger_identifiants_principaux() -> Dict[str, str]:
    """
    Charge les identifiants (username/password) depuis le fichier auth.env principal.

    Returns
    -------
    Dict[str, str]
        Dictionnaire contenant CENTRAL_USERNAME et CENTRAL_PASSWORD.

    Raises
    ------
    FileNotFoundError
        Si le fichier auth.env principal n'existe pas.
    ValueError
        Si les variables CENTRAL_USERNAME ou CENTRAL_PASSWORD sont manquantes.
    """
    if not ENV_PRINCIPAL.exists():
        raise FileNotFoundError(
            f"Le fichier auth.env principal est introuvable : {ENV_PRINCIPAL}\n"
            f"Créez ce fichier avec CENTRAL_USERNAME et CENTRAL_PASSWORD."
        )

    valeurs_env = dotenv_values(ENV_PRINCIPAL)

    champs_attendus = {
        "CENTRAL_USERNAME",
        "CENTRAL_PASSWORD",
    }

    manquants = [champ for champ in champs_attendus if not valeurs_env.get(champ)]
    if manquants:
        raise ValueError(
            f"Les variables {', '.join(manquants)} sont manquantes dans {ENV_PRINCIPAL}"
        )

    return {
        "username": valeurs_env["CENTRAL_USERNAME"],
        "password": valeurs_env["CENTRAL_PASSWORD"],
    }


def lister_clients() -> List[str]:
    """
    Retourne la liste des clients disponibles dans le fichier clients_config.py.
    """
    return list(CLIENTS.keys())


def charger_central_info(nom_client: str) -> Dict[str, str]:
    """
    Charge les informations de connexion Aruba Central pour un client donné.
    
    Les identifiants (username/password) sont chargés depuis le fichier auth.env principal,
    tandis que les autres paramètres (client_id, client_secret, customer_id, base_url)
    sont chargés depuis le fichier .env du client.

    Parameters
    ----------
    nom_client : str
        Nom du client tel que défini dans clients_config.CLIENTS.

    Returns
    -------
    Dict[str, str]
        Dictionnaire contenant les informations nécessaires pour initialiser ArubaCentralBase.
    """
    if nom_client not in CLIENTS:
        raise ValueError(f"Client inconnu : {nom_client}. Vérifiez clients_config.py.")

    chemin_env = CLIENTS[nom_client]
    if not os.path.exists(chemin_env):
        raise FileNotFoundError(
            f"Le fichier .env pour le client '{nom_client}' est introuvable : {chemin_env}"
        )

    # Charger les identifiants depuis le fichier .env principal
    identifiants = charger_identifiants_principaux()

    # Charger les autres paramètres depuis le fichier .env du client
    valeurs_env = dotenv_values(chemin_env)

    champs_attendus = {
        "CLIENT_ID",
        "CLIENT_SECRET",
        "CUSTOMER_ID",
        "BASE_URL",
    }

    manquants = [champ for champ in champs_attendus if not valeurs_env.get(champ)]
    if manquants:
        raise ValueError(
            f"Les variables {', '.join(manquants)} sont manquantes dans {chemin_env}"
        )

    return {
        "client_id": valeurs_env["CLIENT_ID"],
        "client_secret": valeurs_env["CLIENT_SECRET"],
        "customer_id": valeurs_env["CUSTOMER_ID"],
        "username": identifiants["username"],
        "password": identifiants["password"],
        "base_url": valeurs_env["BASE_URL"],
    }

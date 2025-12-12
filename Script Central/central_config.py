"""
Module de configuration pour la connexion à Aruba Central.

Ce module se charge de récupérer les informations de connexion
pour un client donné à partir d'un fichier .env spécifique.
"""

from typing import Dict, List
import os

from dotenv import dotenv_values

from clients_config import CLIENTS


def lister_clients() -> List[str]:
    """
    Retourne la liste des clients disponibles dans le fichier clients_config.py.
    """
    return list(CLIENTS.keys())


def charger_central_info(nom_client: str) -> Dict[str, str]:
    """
    Charge les informations de connexion Aruba Central pour un client donné.

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

    valeurs_env = dotenv_values(chemin_env)

    champs_attendus = {
        "CLIENT_ID",
        "CLIENT_SECRET",
        "CUSTOMER_ID",
        "CENTRAL_USERNAME",
        "CENTRAL_PASSWORD",
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
        "username": valeurs_env["CENTRAL_USERNAME"],
        "password": valeurs_env["CENTRAL_PASSWORD"],
        "base_url": valeurs_env["BASE_URL"],
    }

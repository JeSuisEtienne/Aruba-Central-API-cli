"""
Définition dynamique de la liste des clients à partir du dossier `.env`.

Chaque fichier `.env` représente un client et doit contenir les variables :
    CLIENT_ID, CLIENT_SECRET, CUSTOMER_ID,
    CENTRAL_USERNAME, CENTRAL_PASSWORD, BASE_URL

Le nom du client affiché dans le script correspond au nom du fichier sans l'extension `.env`.
"""

from pathlib import Path
from typing import Dict


ENV_DIR = Path(__file__).resolve().parent / ".env"


def charger_clients_depuis_dossier(env_dir: Path = ENV_DIR) -> Dict[str, str]:
    """
    Scanne le dossier `.env` et retourne un dictionnaire {nom_client: chemin_fichier}.
    """
    if not env_dir.exists():
        raise RuntimeError(
            f"Le dossier {env_dir} n'existe pas. Créez-le et ajoutez des fichiers .env."
        )

    fichiers_env = sorted(env_dir.glob("*.env"))
    if not fichiers_env:
        raise RuntimeError(
            f"Aucun fichier .env trouvé dans {env_dir}. Ajoutez au moins un fichier client."
        )

    return {fichier.stem: str(fichier) for fichier in fichiers_env}


# Dictionnaire chargé dynamiquement à l'import du module
CLIENTS = charger_clients_depuis_dossier()


def verifier_configuration() -> None:
    """
    Fonction utilitaire (optionnelle) pour vérifier qu'au moins un client est disponible.
    """
    if not CLIENTS:
        raise RuntimeError(
            "Aucun client détecté dans le dossier .env. "
            "Ajoutez au moins un fichier .env contenant la configuration du client."
        )


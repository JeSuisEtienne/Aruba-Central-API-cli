"""
Script principal pour générer un rapport d'inventaire et de firmware depuis Aruba Central.

Ce script se connecte à l'API Aruba Central, récupère les informations d'inventaire
et de firmware des équipements, puis les exporte dans un fichier Excel formaté.
"""

import os
from typing import List

from pycentral.base import ArubaCentralBase

from central_config import charger_central_info, lister_clients
from data_pipeline import collect_datasets
from excel_export import export_to_excel
from email_sender import charger_config_email, envoyer_email_avec_piece_jointe


def demander_client() -> str:
    """
    Affiche la liste des clients configurés et demande à l'utilisateur
    de sélectionner celui pour lequel les requêtes doivent être effectuées.
    """
    clients_disponibles: List[str] = lister_clients()

    if not clients_disponibles:
        raise RuntimeError(
            "Aucun client n'est configuré. Veuillez ajouter des entrées dans clients_config.py."
        )

    print("Sélectionnez le client pour lequel exécuter les requêtes API :")
    for index, nom_client in enumerate(clients_disponibles, start=1):
        print(f"  {index}. {nom_client}")

    while True:
        choix = input("Entrez le numéro ou le nom du client : ").strip()

        if choix.isdigit():
            position = int(choix)
            if 1 <= position <= len(clients_disponibles):
                return clients_disponibles[position - 1]
            print("Numéro invalide. Merci de réessayer.")
            continue

        if choix in clients_disponibles:
            return choix

        print("Sélection invalide. Merci de réessayer.")


def main() -> None:
    """
    Fonction principale qui orchestre la récupération des données et l'export Excel.
    
    Étapes :
    1. Configuration de la connexion à Aruba Central
    2. Récupération des données d'inventaire et de firmware
    3. Export des données dans un fichier Excel avec formatage
    """
    # Configuration de la vérification SSL (True = vérification activée)
    ssl_verify: bool = True
    
    # 📁 Répertoires de travail (tokens et exports)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_store_dir = os.path.join(script_dir, "temp")
    report_dir = os.path.join(script_dir, "Report")
    
    # Sélection du client et chargement de sa configuration
    nom_client_selectionne = demander_client()
    central_info = charger_central_info(nom_client_selectionne)
    print(f"🔌 Client sélectionné : {nom_client_selectionne}")

    base_url = central_info.get("base_url")
    if not base_url:
        raise ValueError(
            "La variable BASE_URL est absente du fichier .env du client sélectionné."
        )

    # Affichage de la base URL utilisée pour le débogage
    print(f"🌐 Base URL utilisée : {base_url}")

    # 📁 Dossier de tokens isolé par client pour éviter les conflits entre sites
    # Chaque client a son propre dossier de tokens basé sur son nom
    token_dir_client = os.path.join(token_store_dir, nom_client_selectionne)
    os.makedirs(token_dir_client, exist_ok=True)
    print(f"🔐 Dossier de tokens : {token_dir_client}")

    # Création des dossiers nécessaires
    os.makedirs(report_dir, exist_ok=True)

    # Fichier Excel nommé selon le client sélectionné
    fichier_excel = os.path.join(report_dir, f"{nom_client_selectionne}.xlsx")

    # Définition de la variable d'environnement pour que les modules utilisent le bon dossier de tokens
    # Cela permet à script_load_token.load_token() de trouver automatiquement le bon token
    os.environ["CENTRAL_TOKEN_DIR"] = token_dir_client

    # Initialisation de la connexion à Aruba Central
    # central_info contient les informations de connexion (client_id, client_secret, etc.)
    central = ArubaCentralBase(
        central_info=central_info,
        token_store={"path": token_dir_client},  # Dossier de tokens spécifique au client
        ssl_verify=ssl_verify,
    )

    try:
        jeux_de_donnees = collect_datasets(central=central, base_url=base_url)
        export_to_excel(fichier_excel, jeux_de_donnees)
        print(f"✅ Rapport Excel généré : {fichier_excel}")
        """   
        # Envoi par email si configuré
        config_email = charger_config_email(nom_client_selectionne)
        if config_email:
            print("📧 Configuration email détectée, envoi du rapport...")
            envoyer_email_avec_piece_jointe(
                fichier_excel=fichier_excel,
                nom_client=nom_client_selectionne,
                config_email=config_email,
            )
        else:
            print("ℹ️  Aucune configuration email trouvée. Le rapport a été sauvegardé localement.")
        """
    except Exception as e:
        # Gestion des erreurs : affichage de tout problème survenu pendant l'exécution
        print("❌ Une erreur s'est produite :", str(e))


# Point d'entrée du script : exécution de la fonction main() uniquement si le script est lancé directement
# (et non importé comme module)
if __name__ == "__main__":
    main()
"""
Script principal pour générer un rapport MRT (Monitoring Reports & Troubleshooting) 
depuis l'API Aruba Central.

⚠️ IMPORTANT : Ce script utilise la nouvelle authentification OAuth2 pour New Central.
Il ne nécessite pas pycentral.base.ArubaCentralBase et utilise directement OAuth2.

Ce script permet de :
1. CRÉER un nouveau rapport (one-time ou programmé)
2. Lister les rapports programmés
3. Récupérer des rapports spécifiques

Utilisation:
    python "Script Central/main_mrt.py"
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from central_config import charger_central_info, lister_clients
from script_mrt_reports import (
    creer_rapport_programme,
    lister_sites,
)


def demander_client() -> str:
    """
    Affiche la liste des clients configurés et demande à l'utilisateur
    de sélectionner celui pour lequel les requêtes doivent être effectuées.
    """
    clients_disponibles = lister_clients()

    if not clients_disponibles:
        raise RuntimeError(
            "Aucun client n'est configuré. Veuillez ajouter des entrées dans clients_config.py."
        )

    print("\n📋 Sélectionnez le client pour lequel exécuter les requêtes API MRT :")
    for index, nom_client in enumerate(clients_disponibles, start=1):
        print(f"  {index}. {nom_client}")

    while True:
        choix = input("\nEntrez le numéro ou le nom du client : ").strip()

        if choix.isdigit():
            position = int(choix)
            if 1 <= position <= len(clients_disponibles):
                return clients_disponibles[position - 1]
            print("❌ Numéro invalide. Merci de réessayer.")
            continue

        if choix in clients_disponibles:
            return choix

        print("❌ Sélection invalide. Merci de réessayer.")


def demander_type_rapport() -> str:
    """Demande le type de rapport à créer."""
    types_rapports = {
        "1": ("inventory", "Inventory - Liste des équipements"),
        "2": ("clientInventory", "Client Inventory - Inventaire des clients"),
        "3": ("clientSession", "Client Session - Sessions clients"),
        "4": ("appAnalytics", "Application Analytics - Analyses d'applications"),
        "5": ("deviceUptime", "Device Uptime - Temps de disponibilité des équipements"),
        "6": ("networkUsage", "Network Usage - Utilisation du réseau"),
        "7": ("resourceUtilization", "Resource Utilization - Utilisation des ressources"),
        "8": ("capacityPlanning", "Capacity Planning - Planification de capacité"),
        "9": ("rfHealth", "RF Health - Santé RF"),
        "10": ("custom", "Custom - Rapport personnalisé"),
    }
    
    print("\n📊 Sélectionnez le type de rapport à créer :")
    for key, (_, description) in types_rapports.items():
        print(f"  {key}. {description}")
    
    while True:
        choix = input("\nEntrez le numéro du type de rapport : ").strip()
        if choix in types_rapports:
            return types_rapports[choix][0]
        print("❌ Choix invalide. Veuillez choisir un numéro valide.")


def demander_periode_rapport() -> Dict[str, Any]:
    """Demande la période pour le rapport."""
    print("\n📅 Sélectionnez la période du rapport :")
    print("  1. Dernier jour (LAST_DAY)")
    print("  2. Dernière semaine (LAST_WEEK)")
    print("  3. Dernier mois (LAST_MONTH)")
    print("  4. Plage personnalisée (CUSTOM_RANGE)")
    
    choix = input("\nEntrez votre choix (1-4) : ").strip()
    
    if choix == "1":
        return {"reportPeriod": {"type": "LAST_DAY"}}
    elif choix == "2":
        return {"reportPeriod": {"type": "LAST_WEEK"}}
    elif choix == "3":
        return {"reportPeriod": {"type": "LAST_MONTH"}}
    elif choix == "4":
        print("\n⚠️  Plage personnalisée :")
        try:
            jours = int(input("Nombre de jours en arrière : "))
            end_time = datetime.now()
            start_time = end_time - timedelta(days=jours)
            return {
                "reportPeriod": {
                    "type": "CUSTOM_RANGE",
                    "from": int(start_time.timestamp()),
                    "to": int(end_time.timestamp()),
                }
            }
        except ValueError:
            print("❌ Nombre invalide. Utilisation de la dernière semaine par défaut.")
            return {"reportPeriod": {"type": "LAST_WEEK"}}
    else:
        print("❌ Choix invalide. Utilisation de la dernière semaine par défaut.")
        return {"reportPeriod": {"type": "LAST_WEEK"}}


def demander_schedule() -> Dict[str, Any]:
    """Demande la planification du rapport."""
    print("\n⏰ Planification du rapport :")
    print("  1. Une seule fois (ONE_TIME)")
    print("  2. Quotidien (EVERY_DAY)")
    print("  3. Hebdomadaire (EVERY_WEEK)")
    print("  4. Mensuel (EVERY_MONTH)")
    
    choix = input("\nEntrez votre choix (1-4) : ").strip()
    
    if choix == "1":
        return {"reportSchedule": {"scheduleType": "ONE_TIME"}}
    elif choix in ["2", "3", "4"]:
        try:
            start_date = input("Date de début (YYYY-MM-DD) : ").strip()
            end_date = input("Date de fin (YYYY-MM-DD) : ").strip()
            
            schedule_types = {"2": "EVERY_DAY", "3": "EVERY_WEEK", "4": "EVERY_MONTH"}
            return {
                "reportSchedule": {
                    "scheduleType": schedule_types[choix],
                    "startDate": start_date,
                    "endDate": end_date,
                }
            }
        except Exception:
            print("❌ Format de date invalide. Utilisation de ONE_TIME par défaut.")
            return {"reportSchedule": {"scheduleType": "ONE_TIME"}}
    else:
        print("❌ Choix invalide. Utilisation de ONE_TIME par défaut.")
        return {"reportSchedule": {"scheduleType": "ONE_TIME"}}


def demander_site(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
) -> Optional[List[Dict[str, str]]]:
    """
    Demande à l'utilisateur de sélectionner un site ou tous les sites.
    
    Parameters
    ----------
    base_url : str
        URL de base Aruba Central
    customer_id : str
        ID du client/customer dans Aruba Central
    client_id : str
        ID du client OAuth2 pour l'authentification
    client_secret : str
        Secret du client OAuth2 pour l'authentification
        
    Returns
    -------
    Optional[List[Dict[str, str]]]
        None si "global" est sélectionné,
        Liste vide [] si "tous les sites disponibles" est sélectionné (pour créer un rapport par site),
        Liste avec un seul dict {"id": <site_id>, "name": <site_name>} si un site spécifique est sélectionné
    """
    print("\n🏢 Sélection du site :")
    print("  1. Global (un seul rapport global)")
    print("  2. Tous les sites disponibles (un rapport par site)")
    print("  3. Sélectionner un site spécifique")
    
    choix = input("\nEntrez votre choix (1-3) : ").strip()
    
    if choix == "1":
        return None  # None signifie "global"
    elif choix == "2":
        try:
            # Récupérer la liste de tous les sites disponibles
            sites_disponibles = lister_sites(
                base_url=base_url,
                customer_id=customer_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            if not sites_disponibles:
                print("⚠️ Aucun site trouvé. Utilisation de 'global' par défaut.")
                return None
            
            print(f"\n✅ {len(sites_disponibles)} site(s) trouvé(s). Un rapport sera créé pour chaque site.")
            # Retourner une liste vide pour indiquer "tous les sites disponibles"
            # La liste complète sera récupérée dans main()
            return []
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des sites : {str(e)}")
            print("⚠️ Utilisation de 'global' par défaut.")
            return None
    elif choix == "3":
        try:
            # Récupérer la liste des sites disponibles
            sites_disponibles = lister_sites(
                base_url=base_url,
                customer_id=customer_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            if not sites_disponibles:
                print("⚠️ Aucun site trouvé. Utilisation de 'global' par défaut.")
                return None
            
            print(f"\n📋 Sites disponibles ({len(sites_disponibles)}) :")
            for index, site in enumerate(sites_disponibles, start=1):
                nom_site = site.get("name", "N/A")
                site_id = site.get("id", "N/A")
                print(f"  {index}. {nom_site} (id: {site_id})")
            
            while True:
                choix_site = input("\nEntrez le numéro ou le nom du site : ").strip()
                
                if choix_site.isdigit():
                    position = int(choix_site)
                    if 1 <= position <= len(sites_disponibles):
                        site_selectionne = sites_disponibles[position - 1]
                        print(f"✅ Site sélectionné : {site_selectionne.get('name', 'N/A')} (id: {site_selectionne.get('id', 'N/A')})")
                        return [site_selectionne]  # Retourner une liste avec un seul site
                    print("❌ Numéro invalide. Merci de réessayer.")
                    continue
                
                # Recherche par nom exact
                site_trouve = next(
                    (s for s in sites_disponibles if s.get("name") == choix_site),
                    None,
                )
                if site_trouve:
                    print(f"✅ Site sélectionné : {site_trouve.get('name', 'N/A')} (id: {site_trouve.get('id', 'N/A')})")
                    return [site_trouve]  # Retourner une liste avec un seul site
                
                print("❌ Sélection invalide. Merci de réessayer.")
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des sites : {str(e)}")
            print("⚠️ Utilisation de 'global' par défaut.")
            return None
    else:
        print("❌ Choix invalide. Utilisation de 'global' par défaut.")
        return None


def main() -> None:
    """
    Fonction principale qui orchestre la récupération des rapports MRT et l'export Excel.
    
    ⚠️ Utilise la nouvelle authentification OAuth2 pour New Central.
    """
    # Répertoires de travail
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_dir = os.path.join(script_dir, "Report")
    
    # Sélection du client et chargement de sa configuration
    nom_client_selectionne = demander_client()
    central_info = charger_central_info(nom_client_selectionne)
    print(f"\n🔌 Client sélectionné : {nom_client_selectionne}")

    base_url = central_info.get("base_url")
    if not base_url:
        raise ValueError(
            "La variable BASE_URL est absente du fichier .env du client sélectionné."
        )

    customer_id = central_info.get("customer_id")
    if not customer_id:
        raise ValueError(
            "La variable CUSTOMER_ID est absente du fichier .env du client sélectionné."
        )

    client_id = central_info.get("client_id")
    if not client_id:
        raise ValueError(
            "La variable CLIENT_ID est absente du fichier .env du client sélectionné."
        )

    client_secret = central_info.get("client_secret")
    if not client_secret:
        raise ValueError(
            "La variable CLIENT_SECRET est absente du fichier .env du client sélectionné."
        )

    print(f"🌐 Base URL utilisée : {base_url}")
    print(f"🆔 Customer ID : {customer_id}")
    print(f"🔑 Authentification OAuth2 activée pour New Central")

    # Création des dossiers nécessaires
    os.makedirs(report_dir, exist_ok=True)

    try:
        print("\n" + "="*60)
        print("📊 Création d'un rapport MRT...")
        print("="*60)
        
        # Demander les paramètres essentiels
        type_rapport = demander_type_rapport()
        periode_config = demander_periode_rapport()
        schedule_config = demander_schedule()
        
        # Demander la sélection du site
        sites_selectionnes = demander_site(
            base_url=base_url,
            customer_id=customer_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        
        # Déterminer la liste des sites pour lesquels créer des rapports
        # None = global, [] = tous les sites disponibles (un rapport par site), [site] = un site spécifique
        if sites_selectionnes is None:
            # Option 1: Global - un seul rapport global
            sites_a_traiter = None
            scope_info = "Global (tous les sites)"
        elif len(sites_selectionnes) == 0:
            # Option 2: Tous les sites disponibles - un rapport par site
            sites_disponibles = lister_sites(
                base_url=base_url,
                customer_id=customer_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            sites_a_traiter = sites_disponibles
            scope_info = f"Tous les sites disponibles ({len(sites_a_traiter)} site(s)) - un rapport par site"
        else:
            # Option 3: Un site spécifique
            sites_a_traiter = sites_selectionnes
            scope_info = f"Site: {sites_a_traiter[0].get('name', 'N/A')} (id: {sites_a_traiter[0].get('id', 'N/A')})"
        
        # Préparer la configuration commune du rapport
        report_period = periode_config.get("reportPeriod", {})
        
        # reportSchedule doit avoir "recurrenceType" au lieu de "scheduleType"
        report_schedule = schedule_config.get("reportSchedule", {})
        if "scheduleType" in report_schedule:
            report_schedule = {"recurrenceType": report_schedule["scheduleType"]}
            # Conserver startDate/endDate si présents
            if "startDate" in schedule_config.get("reportSchedule", {}):
                report_schedule["startDate"] = schedule_config["reportSchedule"]["startDate"]
            if "endDate" in schedule_config.get("reportSchedule", {}):
                report_schedule["endDate"] = schedule_config["reportSchedule"]["endDate"]
        elif "recurrenceType" not in report_schedule:
            # Si déjà au bon format, utiliser directement
            pass
        
        # Fonction pour créer un rapport avec un scope donné
        def creer_rapport_avec_scope(
            is_global: bool,
            site_ids: Optional[List[str]] = None,
            nom_site: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Crée un rapport avec le scope spécifié.
            
            Parameters
            ----------
            is_global : bool
                True si c'est un rapport global, False si c'est pour des sites spécifiques
            site_ids : Optional[List[str]]
                Liste des IDs de sites (requis si is_global=False)
            nom_site : Optional[str]
                Nom du site pour le nom du rapport (optionnel)
            """
            # Génération du nom du rapport
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if nom_site:
                nom_rapport = f"Rapport_{type_rapport}_{nom_site}_{nom_client_selectionne}_{timestamp}"
            else:
                nom_rapport = f"Rapport_{type_rapport}_{nom_client_selectionne}_{timestamp}"
            
            filters_list: List[Dict[str, Any]] = []
            
            # Construire les filtres selon le type de scope
            if is_global:
                # Pour global : seulement le filtre scope avec ["global"]
                filters_list.append({
                    "filterType": "scope",
                    "values": ["global"]
                })
            else:
                # Pour les sites : filtre scope avec ["sites"] ET filtre sites avec les IDs
                if not site_ids:
                    raise ValueError("Les IDs de sites sont requis pour un rapport par site")
                
                filters_list.append({
                    "filterType": "scope",
                    "values": ["sites"]
                })
                filters_list.append({
                    "filterType": "sites",
                    "values": site_ids
                })
            
            # Ajouter deviceTypes si requis pour le type de rapport
            if type_rapport in ["inventory", "clientInventory", "deviceUptime", "networkUsage", 
                               "resourceUtilization", "capacityPlanning"]:
                filters_list.append({
                    "filterType": "deviceTypes",
                    "values": ["access_points", "switches", "gateways"]
                })
            
            rapport_config: Dict[str, Any] = {
                "report": {
                    "name": nom_rapport,
                    "type": type_rapport,
                    "timeZone": "Europe/Paris",  # Fuseau horaire par défaut
                    "filters": filters_list,
                    "reportPeriod": report_period,
                    "reportSchedule": report_schedule,
                }
            }
            
            return creer_rapport_programme(
                base_url=base_url,
                customer_id=customer_id,
                client_id=client_id,
                client_secret=client_secret,
                rapport_config=rapport_config,
            )
        
        # Créer les rapports selon le choix
        print(f"\n🔗 Création du/des rapport(s)...")
        print(f"   Type: {type_rapport}")
        periode_type = report_period.get('type', 'N/A')
        print(f"   Période: {periode_type}")
        print(f"   Planification: {report_schedule.get('recurrenceType', 'N/A')}")
        print(f"   Scope: {scope_info}")
        
        if sites_a_traiter is None:
            # Option 1: Global - un seul rapport
            print(f"\n📊 Création d'un rapport global...")
            resultat = creer_rapport_avec_scope(is_global=True)
            print(f"\n✅ Rapport créé avec succès !")
            if "id" in resultat:
                print(f"   ID du rapport: {resultat.get('id')}")
            if "name" in resultat:
                print(f"   Nom: {resultat.get('name')}")
        elif len(sites_a_traiter) == 1:
            # Option 3: Un site spécifique - un seul rapport
            site = sites_a_traiter[0]
            site_id = site.get("id")
            site_name = site.get("name", "N/A")
            
            print(f"\n📊 Création d'un rapport pour le site: {site_name} (id: {site_id})...")
            try:
                resultat = creer_rapport_avec_scope(
                    is_global=False,
                    site_ids=[site_id],
                    nom_site=site_name
                )
                print(f"\n✅ Rapport créé avec succès !")
                if "id" in resultat:
                    print(f"   ID du rapport: {resultat.get('id')}")
                if "name" in resultat:
                    print(f"   Nom: {resultat.get('name')}")
            except Exception as e:
                print(f"\n❌ Erreur lors de la création du rapport: {str(e)}")
        else:
            # Option 2: Tous les sites disponibles - un rapport par site
            nombre_rapports = len(sites_a_traiter)
            print(f"\n📊 Création de {nombre_rapports} rapport(s) (un par site)...")
            
            rapports_crees = 0
            rapports_echoues = 0
            
            for index, site in enumerate(sites_a_traiter, start=1):
                site_id = site.get("id")
                site_name = site.get("name", "N/A")
                
                print(f"\n   [{index}/{nombre_rapports}] Création du rapport pour le site: {site_name} (id: {site_id})")
                
                try:
                    resultat = creer_rapport_avec_scope(
                        is_global=False,
                        site_ids=[site_id],
                        nom_site=site_name
                    )
                    rapports_crees += 1
                    if "id" in resultat:
                        print(f"      ✅ Rapport créé - ID: {resultat.get('id')}")
                    if "name" in resultat:
                        print(f"      Nom: {resultat.get('name')}")
                except Exception as e:
                    rapports_echoues += 1
                    print(f"      ❌ Erreur lors de la création du rapport: {str(e)}")
            
            print(f"\n📊 Résumé:")
            print(f"   ✅ Rapports créés avec succès: {rapports_crees}/{nombre_rapports}")
            if rapports_echoues > 0:
                print(f"   ❌ Rapports échoués: {rapports_echoues}/{nombre_rapports}")
        
    except Exception as e:
        print(f"\n❌ Une erreur s'est produite : {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


"""
Module pour récupérer et générer des rapports MRT (Monitoring Reports & Troubleshooting) 
via l'API Aruba Central.

Ce module utilise la nouvelle authentification OAuth2 pour New Central :
- Authentification via BackendApplicationClient et OAuth2Session
- Token URL: https://sso.common.cloud.hpe.com/as/token.oauth2
- Grant type: client_credentials

Ce module permet de :
- Lister les rapports générés disponibles
- Lister les rapports programmés
- Récupérer un rapport généré spécifique
- Créer/supprimer des rapports programmés

Les endpoints utilisés sont basés sur l'API Reporting de New Central :
- GET /network-reporting/v1alpha1/reports - Liste tous les rapports
- GET /network-reporting/v1alpha1/report-runs - Liste les exécutions de rapports (rapports générés)
- POST /network-reporting/v1alpha1/reports - Créer un nouveau rapport
- GET /network-reporting/v1alpha1/reports/{report_id} - Récupérer un rapport spécifique

Documentation: https://developer.arubanetworks.com/new-central/reference/createuserreport
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
import pandas as pd
import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session


# URL du serveur d'authentification OAuth2 pour New Central
NEW_CENTRAL_TOKEN_URL = "https://sso.common.cloud.hpe.com/as/token.oauth2"


def obtenir_token_oauth2(client_id: str, client_secret: str) -> str:
    """
    Obtient un token d'accès OAuth2 pour New Central via client credentials.
    
    Cette fonction utilise la nouvelle méthode d'authentification OAuth2
    spécifique à New Central avec BackendApplicationClient.
    
    Parameters
    ----------
    client_id : str
        ID du client OAuth2 (CLIENT_ID)
    client_secret : str
        Secret du client OAuth2 (CLIENT_SECRET)
        
    Returns
    -------
    str
        Le token d'accès OAuth2 (access_token)
        
    Raises
    ------
    ValueError
        Si l'authentification échoue
    """
    try:
        # Création du client OAuth2
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        
        # Préparation du body pour la requête de token
        body = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"
        
        # Obtention du token
        token = oauth.fetch_token(token_url=NEW_CENTRAL_TOKEN_URL, body=body)
        
        access_token = token.get("access_token")
        if not access_token:
            raise ValueError("❌ Le token d'accès n'a pas été retourné par le serveur OAuth2.")
        
        return access_token
        
    except Exception as e:
        raise ValueError(f"❌ Erreur lors de l'authentification OAuth2 : {str(e)}")


def _obtenir_headers(client_id: str, client_secret: str, customer_id: Optional[str] = None) -> Dict[str, str]:
    """
    Construit les en-têtes HTTP nécessaires pour les appels API MRT.
    
    Utilise la nouvelle authentification OAuth2 pour New Central.
    
    Parameters
    ----------
    client_id : str
        ID du client OAuth2
    client_secret : str
        Secret du client OAuth2
    customer_id : Optional[str]
        ID du client/customer (optionnel, ajouté dans les headers si fourni)
    
    Returns
    -------
    Dict[str, str]
        Dictionnaire contenant les en-têtes HTTP avec le token d'authentification
    """
    access_token = obtenir_token_oauth2(client_id, client_secret)
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    if customer_id:
        headers["X-Customer-Id"] = customer_id
    
    return headers


def lister_sites(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
    limit: int = 1000,
) -> List[Dict[str, str]]:
    """
    Récupère la liste des sites disponibles depuis l'API Aruba Central.
    
    Utilise l'endpoint network-monitoring/v1alpha1/sites-health pour obtenir
    les couples (id, name) des sites.
    
    Parameters
    ----------
    base_url : str
        URL de base Aruba Central (ex: https://de1.api.central.arubanetworks.com)
    customer_id : str
        ID du client/customer dans Aruba Central
    client_id : str
        ID du client OAuth2 pour l'authentification
    client_secret : str
        Secret du client OAuth2 pour l'authentification
    limit : int
        Nombre maximum de sites à récupérer (pagination interne, par défaut: 1000)
        
    Returns
    -------
    List[Dict[str, str]]
        Liste de dictionnaires contenant au minimum:
        - "id": identifiant technique du site (ex: "45360330107731968")
        - "name": nom du site (ex: "LHA_Vernouillet")
    """
    headers = _obtenir_headers(client_id, client_secret, customer_id)
    
    endpoint = base_url.rstrip("/") + "/network-monitoring/v1alpha1/sites-health"
    print(f"🔗 Récupération des sites depuis l'API network-monitoring/v1alpha1/sites-health...")
    
    offset = 0
    limit_page = 100
    sites: List[Dict[str, str]] = []
    
    while offset < limit:
        params = {"limit": limit_page, "offset": offset}
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"⚠️ Erreur {response.status_code} lors de la récupération des sites: {response.text[:200]}")
                break
            
            payload = response.json() if response.text else {}
            items = payload.get("items") or payload.get("data") or []
            
            if not items:
                break
            
            for item in items:
                site_id = item.get("id")
                site_name = item.get("name")
                if site_id and site_name:
                    sites.append({"id": str(site_id), "name": str(site_name)})
            
            if len(items) < limit_page:
                break
            offset += limit_page
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des sites: {str(e)}")
            break
    
    # Supprimer les doublons éventuels par id, garder le premier nom rencontré
    sites_uniques: Dict[str, str] = {}
    for s in sites:
        if s["id"] not in sites_uniques:
            sites_uniques[s["id"]] = s["name"]
    
    sites_liste = [
        {"id": site_id, "name": name}
        for site_id, name in sorted(sites_uniques.items(), key=lambda x: x[1])
    ]
    
    print(f"✅ {len(sites_liste)} site(s) trouvé(s).")
    
    return sites_liste


def lister_rapports_generes(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> pd.DataFrame:
    """
    Liste les rapports générés disponibles dans Aruba Central.
    
    Parameters
    ----------
    base_url : str
        URL de base Aruba Central (ex: https://apigw-eucentral3.central.arubanetworks.com)
    customer_id : str
        ID du client/customer dans Aruba Central
    client_id : str
        ID du client OAuth2 pour l'authentification
    client_secret : str
        Secret du client OAuth2 pour l'authentification
    start_time : Optional[int]
        Timestamp Unix (epoch) de début de période (optionnel)
    end_time : Optional[int]
        Timestamp Unix (epoch) de fin de période (optionnel)
    limit : int
        Nombre maximum de résultats à retourner (par défaut: 100)
    offset : int
        Décalage pour la pagination (par défaut: 0)
        
    Returns
    -------
    pd.DataFrame
        DataFrame contenant la liste des rapports générés avec leurs métadonnées
    """
    headers = _obtenir_headers(client_id, client_secret, customer_id)
    
    params: Dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }
    
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    
    # Ajouter customer_id dans les paramètres si nécessaire
    if customer_id:
        params["customer_id"] = customer_id
    
    # Endpoint correct pour New Central selon la documentation officielle
    # Documentation: https://developer.arubanetworks.com/new-central/reference/createuserreport
    # Pour lister les rapports générés, on utilise "List Report Runs"
    endpoints_to_try = [
        # Format New Central (correct) : /network-reporting/v1alpha1/reports/{report_id}/runs
        # Pour lister tous les runs, on utilise le endpoint sans report_id ou avec des paramètres
        (base_url.rstrip("/") + "/network-reporting/v1alpha1/report-runs", True),
        # Alternative : peut-être qu'il faut lister les rapports d'abord puis leurs runs
        (base_url.rstrip("/") + "/network-reporting/v1alpha1/reports", True),
    ]
    
    response = None
    last_error = None
    
    for endpoint, use_customer_header in endpoints_to_try:
        headers_with_customer = headers.copy()
        if use_customer_header and customer_id:
            headers_with_customer["X-Customer-Id"] = customer_id
        
        print(f"🔗 Tentative avec l'endpoint : {endpoint}")
        
        try:
            response = requests.get(endpoint, headers=headers_with_customer, params=params)
            
            if response.status_code == 200:
                print(f"✅ Endpoint fonctionnel : {endpoint}")
                break
            elif response.status_code == 404:
                print(f"⚠️  Endpoint 404 : {endpoint}, essai suivant...")
                last_error = response.text
                continue
            else:
                # Autre erreur (401, 403, 500, etc.) - on arrête et on remonte l'erreur
                raise ValueError(f"❌ Erreur {response.status_code} : {response.text}")
        except Exception as e:
            print(f"⚠️  Erreur avec {endpoint} : {str(e)}")
            last_error = str(e)
            continue
    
    if not response or response.status_code != 200:
        error_msg = last_error or (response.text if response else "Aucune réponse")
        raise ValueError(
            f"❌ Aucun endpoint valide trouvé pour les rapports générés.\n"
            f"Dernière erreur : {error_msg}\n"
            f"Endpoints testés : {[e[0] for e in endpoints_to_try]}"
        )
    
    data = response.json()
    
    # Pour New Central, selon la documentation, l'endpoint /network-reporting/v1alpha1/reports
    # retourne une liste de rapports, pas des runs. Pour les runs (rapports générés),
    # il faut soit utiliser /network-reporting/v1alpha1/report-runs soit récupérer
    # les runs depuis chaque rapport individuel.
    
    # Pour lister les rapports générés, on doit récupérer tous les rapports
    # puis filtrer ceux qui ont des runs, ou utiliser un endpoint spécifique pour les runs
    
    # Essayons plusieurs clés possibles pour la structure de réponse
    reports = (
        data.get("reportRuns", []) or  # Format pour report-runs
        data.get("runs", []) or        # Format alternatif
        data.get("reports", []) or     # Format standard (liste de rapports)
        data.get("data", []) or        # Format générique
        data.get("items", [])          # Format avec items
    )
    
    # Si data est une liste directement
    if isinstance(data, list):
        reports = data
    
    # Si c'est une liste de rapports, on peut avoir besoin de récupérer leurs runs
    # Pour l'instant, retournons tous les rapports qui ont été générés/exécutés
    # (ceux qui ont des informations de génération)
    
    if not reports:
        print("ℹ️  Aucun rapport généré trouvé pour les critères spécifiés.")
        return pd.DataFrame()
    
    # Conversion en DataFrame
    df = pd.DataFrame(reports)
    print(f"✅ {len(df)} rapport(s) généré(s) trouvé(s).")
    
    return df


def lister_rapports_programmes(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
    limit: int = 100,
    offset: int = 0,
) -> pd.DataFrame:
    """
    Liste les rapports programmés (scheduled reports) dans Aruba Central.
    
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
    limit : int
        Nombre maximum de résultats à retourner (par défaut: 100)
    offset : int
        Décalage pour la pagination (par défaut: 0)
        
    Returns
    -------
    pd.DataFrame
        DataFrame contenant la liste des rapports programmés avec leurs configurations
    """
    headers = _obtenir_headers(client_id, client_secret, customer_id)
    
    params = {
        "limit": limit,
        "offset": offset,
    }
    
    # Ajouter customer_id dans les paramètres si nécessaire
    if customer_id:
        params["customer_id"] = customer_id
    
    # Endpoint correct pour New Central selon la documentation officielle
    # Documentation: https://developer.arubanetworks.com/new-central/reference/createuserreport
    # Pour lister les rapports programmés, on utilise "List Reports" qui retourne tous les rapports (y compris ceux avec schedule)
    endpoints_to_try = [
        # Format New Central (correct) : /network-reporting/v1alpha1/reports
        (base_url.rstrip("/") + "/network-reporting/v1alpha1/reports", True),
    ]
    
    response = None
    last_error = None
    
    for endpoint, use_customer_header in endpoints_to_try:
        headers_with_customer = headers.copy()
        if use_customer_header and customer_id:
            headers_with_customer["X-Customer-Id"] = customer_id
        
        print(f"🔗 Tentative avec l'endpoint : {endpoint}")
        
        try:
            response = requests.get(endpoint, headers=headers_with_customer, params=params)
            
            if response.status_code == 200:
                print(f"✅ Endpoint fonctionnel : {endpoint}")
                break
            elif response.status_code == 404:
                print(f"⚠️  Endpoint 404 : {endpoint}, essai suivant...")
                last_error = response.text
                continue
            else:
                # Autre erreur (401, 403, 500, etc.) - on arrête et on remonte l'erreur
                raise ValueError(f"❌ Erreur {response.status_code} : {response.text}")
        except Exception as e:
            print(f"⚠️  Erreur avec {endpoint} : {str(e)}")
            last_error = str(e)
            continue
    
    if not response or response.status_code != 200:
        error_msg = last_error or (response.text if response else "Aucune réponse")
        raise ValueError(
            f"❌ Aucun endpoint valide trouvé pour les rapports programmés.\n"
            f"Dernière erreur : {error_msg}\n"
            f"Endpoints testés : {[e[0] for e in endpoints_to_try]}"
        )
    
    data = response.json()
    
    # Pour New Central, la structure de réponse peut être différente
    # Essayons plusieurs clés possibles
    reports = (
        data.get("reports", []) or     # Format standard
        data.get("data", []) or        # Format générique
        data.get("items", [])          # Format avec items
    )
    
    # Si data est une liste directement
    if isinstance(data, list):
        reports = data
    
    if not reports:
        print("ℹ️  Aucun rapport programmé trouvé.")
        return pd.DataFrame()
    
    # Filtrer les rapports qui ont une planification (schedule)
    # Les rapports avec reportSchedule sont ceux qui sont programmés
    reports_programmes = [
        r for r in reports 
        if r.get("reportSchedule") or r.get("schedule")
    ] if reports else []
    
    if not reports_programmes:
        print("ℹ️  Aucun rapport programmé trouvé.")
        return pd.DataFrame()
    
    # Conversion en DataFrame
    df = pd.DataFrame(reports_programmes)
    print(f"✅ {len(df)} rapport(s) programmé(s) trouvé(s).")
    
    return df


def recuperer_rapport_genere(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
    report_id: str,
    format: str = "json",
) -> Dict[str, Any]:
    """
    Récupère le contenu d'un rapport généré spécifique.
    
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
    report_id : str
        ID du rapport à récupérer
    format : str
        Format souhaité : "json", "csv", "pdf" (par défaut: "json")
        
    Returns
    -------
    Dict[str, Any]
        Contenu du rapport (format dépend du paramètre format)
    """
    headers = _obtenir_headers(client_id, client_secret, customer_id)
    
    # Endpoint New Central pour récupérer un rapport spécifique
    # Documentation: https://developer.arubanetworks.com/new-central/reference/createuserreport
    endpoint = base_url.rstrip("/") + f"/network-reporting/v1alpha1/reports/{report_id}"
    
    headers_with_customer = headers.copy()
    
    print(f"🔗 Récupération du rapport {report_id}...")
    
    params = {}
    if format != "json":
        params["format"] = format
    
    response = requests.get(endpoint, headers=headers_with_customer, params=params)
    
    if response.status_code != 200:
        raise ValueError(f"❌ Erreur {response.status_code} lors de la récupération du rapport : {response.text}")
    
    if format == "json":
        return response.json()
    elif format == "csv":
        return {"content": response.text, "format": "csv"}
    elif format == "pdf":
        return {"content": response.content, "format": "pdf"}
    else:
        return {"content": response.text, "format": format}


def creer_rapport_programme(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
    rapport_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Crée un nouveau rapport programmé dans Aruba Central.
    
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
    rapport_config : Dict[str, Any]
        Configuration du rapport (type, paramètres, fréquence, etc.)
        
    Returns
    -------
    Dict[str, Any]
        Réponse de l'API contenant les détails du rapport créé
    """
    headers = _obtenir_headers(client_id, client_secret, customer_id)
    
    # Endpoint New Central pour créer un rapport
    # Documentation: https://developer.arubanetworks.com/new-central/reference/createuserreport
    endpoint = base_url.rstrip("/") + "/network-reporting/v1alpha1/reports"
    
    headers_with_customer = headers.copy()
    
    print(f"🔗 Création d'un rapport programmé...")
    
    response = requests.post(endpoint, headers=headers_with_customer, json=rapport_config)
    
    # Debug: afficher la réponse en cas d'erreur
    if response.status_code not in [200, 201]:
        print(f"❌ Réponse de l'API (status {response.status_code}):")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(response.text)
    
    if response.status_code not in [200, 201]:
        raise ValueError(f"❌ Erreur {response.status_code} lors de la création du rapport : {response.text}")
    
    result = response.json()
    print(f"✅ Rapport programmé créé avec succès.")
    
    return result


def _convertir_timestamp_epoch(dt: datetime) -> int:
    """Convertit un datetime Python en timestamp Unix (epoch)."""
    return int(dt.timestamp())


def obtenir_rapports_periode(
    base_url: str,
    customer_id: str,
    client_id: str,
    client_secret: str,
    jours: int = 30,
) -> pd.DataFrame:
    """
    Récupère les rapports générés pour une période donnée (derniers N jours).
    
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
    jours : int
        Nombre de jours en arrière à partir d'aujourd'hui (par défaut: 30)
        
    Returns
    -------
    pd.DataFrame
        DataFrame contenant les rapports générés pour la période spécifiée
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=jours)
    
    start_epoch = _convertir_timestamp_epoch(start_time)
    end_epoch = _convertir_timestamp_epoch(end_time)
    
    print(f"📅 Recherche des rapports entre {start_time.strftime('%Y-%m-%d')} et {end_time.strftime('%Y-%m-%d')}")
    
    return lister_rapports_generes(
        base_url=base_url,
        customer_id=customer_id,
        client_id=client_id,
        client_secret=client_secret,
        start_time=start_epoch,
        end_time=end_epoch,
    )


def exporter_rapports_vers_excel(
    df_rapports_generes: pd.DataFrame,
    df_rapports_programmes: Optional[pd.DataFrame] = None,
    fichier_sortie: str = "rapports_mrt.xlsx",
) -> None:
    """
    Exporte les rapports MRT vers un fichier Excel formaté.
    
    Parameters
    ----------
    df_rapports_generes : pd.DataFrame
        DataFrame contenant les rapports générés
    df_rapports_programmes : Optional[pd.DataFrame]
        DataFrame contenant les rapports programmés (optionnel)
    fichier_sortie : str
        Chemin du fichier Excel de sortie
    """
    import os
    from excel_format import formater_excel
    
    os.makedirs(os.path.dirname(fichier_sortie) if os.path.dirname(fichier_sortie) else ".", exist_ok=True)
    
    # Vérifier qu'au moins un DataFrame contient des données
    has_generated = not df_rapports_generes.empty
    has_scheduled = df_rapports_programmes is not None and not df_rapports_programmes.empty
    
    if not has_generated and not has_scheduled:
        print("⚠️  Aucun rapport à exporter (pas de rapports générés ni programmés).")
        print("ℹ️  Le fichier Excel ne sera pas créé car il n'y a aucune donnée.")
        return
    
    with pd.ExcelWriter(fichier_sortie, engine="openpyxl") as writer:
        if has_generated:
            df_rapports_generes.to_excel(writer, sheet_name="Rapports Générés", index=False)
            formater_excel(writer, "Rapports Générés")
            print(f"✅ Feuille 'Rapports Générés' ajoutée avec {len(df_rapports_generes)} rapport(s).")
        else:
            # Créer une feuille vide avec un message si pas de données
            df_vide = pd.DataFrame({"Message": ["Aucun rapport généré trouvé pour la période spécifiée."]})
            df_vide.to_excel(writer, sheet_name="Rapports Générés", index=False)
            formater_excel(writer, "Rapports Générés")
            print("ℹ️  Feuille 'Rapports Générés' créée (vide).")
        
        if has_scheduled:
            df_rapports_programmes.to_excel(writer, sheet_name="Rapports Programmés", index=False)
            formater_excel(writer, "Rapports Programmés")
            print(f"✅ Feuille 'Rapports Programmés' ajoutée avec {len(df_rapports_programmes)} rapport(s).")
        elif df_rapports_programmes is not None:
            # Créer une feuille vide avec un message si pas de données
            df_vide = pd.DataFrame({"Message": ["Aucun rapport programmé trouvé."]})
            df_vide.to_excel(writer, sheet_name="Rapports Programmés", index=False)
            formater_excel(writer, "Rapports Programmés")
            print("ℹ️  Feuille 'Rapports Programmés' créée (vide).")
    
    print(f"✅ Fichier Excel généré : {os.path.abspath(fichier_sortie)}")


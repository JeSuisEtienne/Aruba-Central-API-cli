"""
Module pour charger et extraire les tokens d'authentification Aruba Central.

Ce module gère le chargement des fichiers de token JSON depuis le système de fichiers
et l'extraction du token d'accès nécessaire pour les appels API.
"""

import os
import json
import glob
from typing import Any, Dict, Optional


def load_token(folder: Optional[str] = None, recursive: bool = True) -> Dict[str, Any]:
    """
    Charge le fichier de token JSON le plus récent depuis un dossier.
    
    Cette fonction recherche les fichiers de token dans un dossier spécifié
    en utilisant des motifs de nom de fichier courants. Elle peut rechercher
    récursivement dans les sous-dossiers et retourne toujours le fichier le plus récent.
    
    Parameters
    ----------
    folder : Optional[str]
        Chemin du dossier où chercher les fichiers de token
        Si None, utilise le dossier "temp" dans le même répertoire que ce script
        Peut être surchargé par la variable d'environnement CENTRAL_TOKEN_DIR
    recursive : bool
        Si True, recherche récursivement dans les sous-dossiers
        Si False, recherche uniquement dans le dossier spécifié
    
    Returns
    -------
    Dict[str, Any]
        Contenu JSON parsé du fichier de token (dictionnaire Python)
    
    Raises
    ------
    FileNotFoundError
        Si le dossier n'existe pas ou si aucun fichier de token n'est trouvé
        Le message d'erreur inclut des informations utiles pour le débogage
    """
    # Résolution du dossier par défaut : dossier "temp" dans le même répertoire que ce script
    # Sauf si un dossier est spécifié explicitement ou via une variable d'environnement
    if folder is None:
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    else:
        default_dir = folder
    
    # Vérification de la variable d'environnement CENTRAL_TOKEN_DIR (priorité la plus haute)
    # Cette variable est définie automatiquement par main.py pour isoler les tokens par client
    folder = os.environ.get("CENTRAL_TOKEN_DIR", default_dir)
    
    # Vérification que le dossier existe
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"❌ Le dossier {folder} n'existe pas.")

    # Motifs de recherche pour les fichiers de token
    # Ces motifs correspondent aux noms de fichiers générés par le SDK Aruba Central
    patterns = [
        "tok_*.json",      # Format standard du SDK (ex: tok_03a7a1a7eb7848559f45c3bd2714cb53_...)
        "token_*.json",    # Format alternatif
    ]

    # Recherche de tous les fichiers correspondant aux motifs
    candidate_paths = []
    for pattern in patterns:
        # Construction du chemin de recherche avec ou sans récursivité
        search_glob = os.path.join(folder, "**", pattern) if recursive else os.path.join(folder, pattern)
        # Extension de la liste avec les fichiers trouvés
        candidate_paths.extend(glob.glob(search_glob, recursive=recursive))

    # Déduplication des chemins tout en préservant l'ordre
    # Utilisation d'un dictionnaire pour supprimer les doublons
    files = list(dict.fromkeys(candidate_paths))

    # Gestion du cas où aucun fichier n'est trouvé
    if not files:
        # Tentative de lister le contenu du dossier pour aider au débogage
        try:
            immediate = sorted(os.listdir(folder))
        except Exception:
            immediate = []
        # Limitation à 20 éléments pour éviter des messages d'erreur trop longs
        hint_listing = ", ".join(immediate[:20]) + (" …" if len(immediate) > 20 else "")
        
        # Levée d'une exception avec des informations détaillées pour faciliter le débogage
        raise FileNotFoundError(
            "❌ Aucun fichier de token trouvé.\n"
            f"Dossier inspecté: {folder}\n"
            f"Récursif: {recursive}\n"
            f"Motifs recherchés: {', '.join(patterns)}\n"
            f"Contenu du dossier (niveau immédiat): {hint_listing or '(vide)'}\n"
            "Vérifiez que le token a bien été téléchargé et placé dans ce dossier."
        )

    # Tri des fichiers par date de modification (le plus récent en premier)
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    # Sélection du fichier le plus récent
    latest_path = files[0]

    # Lecture et parsing du fichier JSON
    with open(latest_path, "r", encoding="utf-8") as f:
        token_data: Dict[str, Any] = json.load(f)

    return token_data


def get_access_token(token_payload: Dict[str, Any]) -> str:
    """
    Extrait le token d'accès depuis un payload de token.
    
    Cette fonction supporte plusieurs variantes de clés pour le token d'accès,
    car différents systèmes peuvent utiliser des noms de clés différents.
    
    Parameters
    ----------
    token_payload : Dict[str, Any]
        Dictionnaire contenant les données du token JSON
        Peut contenir le token sous différentes clés : "access_token", "token", ou "accessToken"
    
    Returns
    -------
    str
        Le token d'accès sous forme de chaîne de caractères
    
    Raises
    ------
    KeyError
        Si aucune des clés attendues n'est trouvée dans le payload
    """
    # Tentative d'extraction du token d'accès avec différentes variantes de clés
    # Ordre de priorité : access_token > token > accessToken
    access_token = (
        token_payload.get("access_token")      # Format standard OAuth2
        or token_payload.get("token")          # Format simplifié
        or token_payload.get("accessToken")    # Format camelCase
    )
    
    # Vérification que le token a bien été trouvé
    if not access_token:
        raise KeyError("❌ Impossible de déterminer 'access_token' dans le token chargé.")
    
    # Conversion en string pour garantir le type de retour
    return str(access_token)

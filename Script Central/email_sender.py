"""
Module pour envoyer des emails avec pièces jointes.

Ce module permet d'envoyer le rapport Excel généré par email.
Les paramètres de configuration email sont chargés depuis le fichier .env du client.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional
from pathlib import Path


def charger_config_email(nom_client: str) -> Optional[Dict[str, str]]:
    """
    Charge la configuration email depuis le fichier .env du client.
    
    Parameters
    ----------
    nom_client : str
        Nom du client pour lequel charger la configuration.
    
    Returns
    -------
    Optional[Dict[str, str]]
        Dictionnaire contenant la configuration email, ou None si non configuré.
    """
    from dotenv import dotenv_values
    from clients_config import CLIENTS
    
    if nom_client not in CLIENTS:
        return None
    
    chemin_env = CLIENTS[nom_client]
    if not os.path.exists(chemin_env):
        return None
    
    valeurs_env = dotenv_values(chemin_env)
    
    # Paramètres email optionnels
    config_email = {
        "smtp_server": valeurs_env.get("SMTP_SERVER"),
        "smtp_port": valeurs_env.get("SMTP_PORT", "587"),
        "smtp_username": valeurs_env.get("SMTP_USERNAME"),
        "smtp_password": valeurs_env.get("SMTP_PASSWORD"),
        "email_from": valeurs_env.get("EMAIL_FROM"),
        "email_to": valeurs_env.get("EMAIL_TO"),
        "email_cc": valeurs_env.get("EMAIL_CC", ""),
        "email_subject": valeurs_env.get("EMAIL_SUBJECT", f"Rapport Aruba Central - {nom_client}"),
    }
    
    # Vérifier si l'email est activé (au moins SMTP_SERVER et EMAIL_TO doivent être définis)
    if not config_email["smtp_server"] or not config_email["email_to"]:
        return None
    
    return config_email


def envoyer_email_avec_piece_jointe(
    fichier_excel: str,
    nom_client: str,
    config_email: Dict[str, str],
) -> bool:
    """
    Envoie un email avec le fichier Excel en pièce jointe.
    
    Parameters
    ----------
    fichier_excel : str
        Chemin vers le fichier Excel à envoyer.
    nom_client : str
        Nom du client (utilisé dans le sujet et le corps de l'email).
    config_email : Dict[str, str]
        Configuration email (serveur SMTP, destinataires, etc.).
    
    Returns
    -------
    bool
        True si l'email a été envoyé avec succès, False sinon.
    """
    if not os.path.exists(fichier_excel):
        print(f"❌ Le fichier Excel est introuvable : {fichier_excel}")
        return False
    
    try:
        # Création du message
        msg = MIMEMultipart()
        msg["From"] = config_email["email_from"]
        msg["To"] = config_email["email_to"]
        
        if config_email.get("email_cc"):
            msg["Cc"] = config_email["email_cc"]
        
        msg["Subject"] = config_email["email_subject"]
        
        # Corps du message
        nom_fichier = os.path.basename(fichier_excel)
        corps_message = f"""
Bonjour,

Veuillez trouver ci-joint le rapport Aruba Central pour le client {nom_client}.

Fichier : {nom_fichier}

Ce rapport a été généré automatiquement et contient :
- L'inventaire des équipements
- Les informations de firmware consolidées

Cordialement,
Système de génération de rapports Aruba Central
"""
        msg.attach(MIMEText(corps_message, "plain", "utf-8"))
        
        # Pièce jointe
        with open(fichier_excel, "rb") as fichier:
            piece_jointe = MIMEBase("application", "octet-stream")
            piece_jointe.set_payload(fichier.read())
        
        encoders.encode_base64(piece_jointe)
        piece_jointe.add_header(
            "Content-Disposition",
            f'attachment; filename= "{nom_fichier}"',
        )
        msg.attach(piece_jointe)
        
        # Connexion au serveur SMTP et envoi
        smtp_port = int(config_email["smtp_port"])
        smtp_server = config_email["smtp_server"]
        
        print(f"📧 Connexion au serveur SMTP : {smtp_server}:{smtp_port}")
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Utiliser TLS si le port est 587
            if smtp_port == 587:
                server.starttls()
            
            # Authentification si nécessaire
            if config_email.get("smtp_username") and config_email.get("smtp_password"):
                server.login(config_email["smtp_username"], config_email["smtp_password"])
            
            # Préparer la liste des destinataires
            destinataires = [config_email["email_to"]]
            if config_email.get("email_cc"):
                destinataires.extend([email.strip() for email in config_email["email_cc"].split(",")])
            
            # Envoi de l'email
            server.send_message(msg, to_addrs=destinataires)
        
        print(f"✅ Email envoyé avec succès à : {', '.join(destinataires)}")
        return True
        
    except smtplib.SMTPException as e:
        print(f"❌ Erreur SMTP lors de l'envoi de l'email : {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {str(e)}")
        return False


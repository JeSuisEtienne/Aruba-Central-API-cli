"""
Module pour récupérer l'inventaire des équipements depuis Aruba Central.

Ce module utilise l'API Aruba Central pour obtenir la liste complète
des équipements gérés et les retourne sous forme de DataFrame pandas.
"""

import pandas as pd
from pycentral.classic.device_inventory import Inventory


def recuperer_inventaire(conn, limit=310):
    """
    Récupère l'inventaire complet des équipements depuis Aruba Central.
    
    Parameters
    ----------
    conn : ArubaCentralBase
        Objet de connexion à Aruba Central (authentifié)
    limit : int, optional
        Nombre maximum d'équipements à récupérer (par défaut: 310)
    
    Returns
    -------
    pd.DataFrame
        DataFrame contenant les informations de tous les équipements
        (colonnes typiques: serial, model, hostname, etc.)
    
    Raises
    ------
    ValueError
        Si la récupération de l'inventaire échoue (code de réponse != 200)
    """
    # Initialisation de l'objet Inventory pour interagir avec l'API
    inventory = Inventory()
    
    # Appel à l'API pour récupérer l'inventaire complet
    # sku_type='all' : récupère tous les types d'équipements (AP, switches, gateways, etc.)
    response = inventory.get_inventory(conn=conn, sku_type='all', limit=limit)
    
    # Vérification du code de réponse HTTP
    if response["code"] == 200:
        # Extraction de la liste des équipements depuis la réponse
        devices = response["msg"]["devices"]
        # Conversion en DataFrame pandas pour faciliter la manipulation des données
        return pd.DataFrame(devices)
    else:
        # Levée d'une exception si la récupération a échoué
        raise ValueError("x❌ Échec lors de la récupération de l'inventaire.")
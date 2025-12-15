"""
Fonctions utilitaires pour générer le rapport Excel.
"""

from __future__ import annotations

import os
from typing import Dict, Iterable

import pandas as pd

from excel_format import formater_excel


def _ecrire_feuille(
    writer: pd.ExcelWriter,
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> None:
    """Écrit une feuille si le DataFrame contient des données."""
    if dataframe is None or dataframe.empty:
        return

    dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    formater_excel(writer, sheet_name)
    print(f"✅ Données {sheet_name} ajoutées à l'Excel.")


def export_to_excel(fichier_excel: str, dataframes: Dict[str, pd.DataFrame]) -> None:
    """
    Exporte les DataFrame fournis dans un fichier Excel structuré.

    Parameters
    ----------
    fichier_excel : str
        Chemin de sortie du fichier Excel.
    dataframes : Dict[str, pd.DataFrame]
        Dictionnaire contenant les différents jeux de données à exporter.
    """
    os.makedirs(os.path.dirname(fichier_excel), exist_ok=True)

    ordre_feuilles: Iterable[tuple[str, str]] = (
        ("firmware_consolide", "Firmware Consolidé"),
        ("inventaire", "Inventaire"),
        ("switches_stack", "Switches (Stack)"),
        ("gateways", "Gateways"),
        ("firmware_switch", "Firmware Switch"),
        ("firmware_swarms", "Firmware Swarms"),
    )

    with pd.ExcelWriter(fichier_excel, engine="openpyxl") as writer:
        for cle, sheet_name in ordre_feuilles:
            _ecrire_feuille(writer, sheet_name, dataframes.get(cle))

    print("✅ Export terminé dans :", os.path.abspath(fichier_excel))


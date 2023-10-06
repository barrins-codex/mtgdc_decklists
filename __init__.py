"""
L'importation des decks de ce module peut se faire de manière simplifiée
en utilisant la classe `ImportDecks` d'abord en indiquant le chemin de
l'importation puis en fournissant les contraintes de l'importation.

```python
decks = ImportDecks.from_directory(my_path)
deck.load_decks(date_from=datetime(2023, 9, 1))
print(f"{len(decks.decks)} decks chargés")
```
"""
import json
import os
import glob
from datetime import datetime
import re

class ImportDecks:
    """Classe qui permet de charger les decks scrappés depuis MTGTOP8."""

    def __init__(self) -> None:
        self.decks = []

    def load_decks(self, date_from="", date_to="", size="") -> None:
        """
        Logique pour la sélection des decks lors de l'importation.

        :param date_from: (datetime object) Date (inclue) de départ de l'importation
        :param date_to: (datetime object) Date (inclue) de fin de l'importation
        :param size: (int) Taille minimale (inclue) du tournoi à importer
        """
        for file in self.files:
            with open(file, "r", encoding="utf-8") as my_file:
                tournoi = json.load(my_file)

            if date_from and datetime.strptime(tournoi["date"], "%d/%m/%y") < date_from:
                continue
            if date_to and datetime.strptime(tournoi["date"], "%d/%m/%y") > date_to:
                continue
            if size and int(re.split(" ", tournoi["players"])[0]) < size:
                continue

            for deck in tournoi["decks"]:
                tmp = []
                deck["decklist"].extend([f"1 {card}" for card in deck["commander"]])
                for card in deck["decklist"]:
                    tmp.append(
                        (int(card.split(" ")[0]), card.split(" ", maxsplit=1)[1])
                    )
                self.decks.append(tmp)

    @staticmethod
    def from_directory(directory_path):
        import_decks = ImportDecks()
        import_decks.files = glob.glob(os.path.join(directory_path, "*.json"))
        return import_decks

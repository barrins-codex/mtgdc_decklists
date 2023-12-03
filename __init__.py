"""
Module: import_decks.py

This module defines the ImportDecks class for importing and processing decks.
"""
import glob
import json
import os
import re
from datetime import datetime


def clean(string: str = "") -> str:
    string = string.lower()
    while string and string[0].isdigit():
        string = string[1:]
    return string if string[0] != " " else string[1:]


class ImportDecks:
    """Class for importing and processing decks."""

    def __init__(self) -> None:
        self.decks = []
        self.files = []

    def load_decks(
        self,
        date_from: datetime = datetime(1993, 8, 5),
        date_to: datetime = datetime.now(),
        **kwargs,
    ) -> None:
        """
        Load decks from files within specified date range and additional criteria.

        Args:
            date_from (datetime): The starting date for filtering decks.
            date_to (datetime): The ending date for filtering decks.
            **kwargs: Additional keyword arguments for filtering decks.

        Keyword Args:
            size (int): Minimum deck size to include.
            commander (list): List of commander names to include.
            cards (list): List of card names to include.

        Returns:
            None
        """
        size = kwargs.get("size", 0)
        commander = kwargs.get("commander", [])
        cards = kwargs.get("cards", [])

        for file in self.files:
            with open(file, "r", encoding="utf-8") as my_file:
                tournoi = json.load(my_file)

            if datetime.strptime(tournoi["date"], "%d/%m/%y") < date_from:
                continue
            if datetime.strptime(tournoi["date"], "%d/%m/%y") > date_to:
                continue
            if size and int(re.split(" ", tournoi["players"])[0]) < size:
                continue

            for deck in tournoi["decks"]:
                dlist = deck["decklist"]
                czone = deck["commander"]
                if self._check(czone, commander) and self._check(dlist + czone, cards):
                    dlist.extend([f"1 {card}" for card in czone])
                    tmp = [
                        (int(card.split(" ")[0]), card.split(" ", maxsplit=1)[1])
                        for card in deck["decklist"]
                    ]
                    self.decks.append(
                        {
                            "deck_id": deck["deck_id"],
                            "decklist": tmp,
                            "commander": czone,
                            "cardlist": [card for (_, card) in tmp],
                        }
                    )

    @staticmethod
    def from_directory(directory_path):
        """
        Create an ImportDecks instance and populate files from a directory.

        Args:
            directory_path (str): Path to the directory containing deck files.

        Returns:
            ImportDecks: An instance of ImportDecks with populated file list.
        """
        import_decks = ImportDecks()
        import_decks.files = sorted(glob.glob(os.path.join(directory_path, "*.json")))
        return import_decks

    @property
    def decklists(self) -> list:
        """
        Get the decklists from the stored decks.

        Returns:
            list: A list of decklists.
        """
        return [deck["decklist"] for deck in self.decks]

    def _check(self, search_list: list, wanted: list) -> bool:
        """
        Get the decklists from the stored decks.

        Returns:
            list: A list of decklists.
        """
        return len(wanted) == 0 or all(
            any(clean(im).startswith(clean(wnt)) for im in search_list) for wnt in wanted
        )

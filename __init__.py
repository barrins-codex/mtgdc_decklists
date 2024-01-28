import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from difflib import HtmlDiff

import textdistance

from mtgdc_carddata import CardDatabase

DATABASE = CardDatabase()


def clean(string: str = "") -> str:
    string = string.lower()
    while string and string[0].isdigit():
        string = string[1:]
    return string if string[0] != " " else string[1:]


class ImportDecks:
    def __init__(self) -> None:
        self.decks = []
        self.files = []

    def load_decks(
        self,
        # date_from: datetime = datetime(1993, 8, 5), # Limited Edition Alpha Release
        date_from: datetime = datetime(2016, 11, 11),  # 20PV official date change
        date_to: datetime = datetime.now(),
        **kwargs,
    ) -> None:
        t_size = kwargs.get("size", 0)
        commander = kwargs.get("commander", [])
        cards = kwargs.get("cards", [])

        player = kwargs.get("player", kwargs.get("alias", []))
        if player:
            p_database = PlayerDatabase()
            player = p_database.check_aliases(player)

        for file in self.files:
            with open(file, "r", encoding="utf-8") as my_file:
                tournoi = json.load(my_file)

            tournoi_date = datetime.strptime(tournoi["date"], "%d/%m/%y")
            if not (date_from <= tournoi_date <= date_to):
                continue

            if not (not t_size or int(re.split(" ", tournoi["players"])[0]) >= t_size):
                continue

            for deck in tournoi["decks"]:
                czone = deck["commander"]
                dlist = deck["decklist"]
                dlist.extend([f"1 {card}" for card in czone])
                tmp = [
                    (int(card.split(" ")[0]), card.split(" ", maxsplit=1)[1])
                    for card in dlist
                ]
                if "Unknown Card" in [card for (_, card) in tmp]:
                    continue

                player_condition = not player or deck["player"] in player
                commander_condition = not commander or ImportDecks.list_check(
                    deck["commander"], commander
                )
                cards_condition = not cards or ImportDecks.list_check(
                    deck["decklist"] + deck["commander"], cards
                )

                if player_condition and commander_condition and cards_condition:
                    self.decks.append(
                        {
                            "t_id": tournoi["id"],
                            "t_size": int(tournoi["players"].split(" ")[0]),
                            "date": tournoi_date.strftime("%Y-%m-%d"),
                            "deck_id": deck["deck_id"],
                            "player": deck["player"],
                            "rank": deck["rank"],
                            "commander": czone,
                            "decklist": tmp,
                            "cardlist": [card for (_, card) in tmp],
                        }
                    )

    @staticmethod
    def from_directory(directory_path: str = "mtgdc_decklists/decklists"):
        import_decks = ImportDecks()
        import_decks.files = sorted(glob.glob(os.path.join(directory_path, "*.json")))
        return import_decks

    @staticmethod
    def list_check(search_list: list, wanted: list) -> bool:
        return len(wanted) == 0 or all(
            any(clean(im).startswith(clean(wnt)) for im in search_list)
            for wnt in wanted
        )

    @property
    def decklists(self) -> list:
        return [deck["decklist"] for deck in self.decks]

    def palmares(self, output: str = "output/palmares.txt", use_url: bool = False):
        results = defaultdict(list)

        for deck in self.decks:
            results[deck["player"]].append(
                {
                    "url": f"https://mtgtop8.com/event?e={deck['t_id']}&d={deck['deck_id']}",
                    "commander": DATABASE.str_command_zone(deck["commander"], " / "),
                    "date": deck["date"],
                    "size": deck["t_size"],
                    "rank": deck["rank"],
                }
            )

        out_str = ["===== Barrin's Data Extraction ====="]
        for player, result in results.items():
            tmp_str = f"\n---------- JOUEUR {len(out_str)} ----------"
            tmp_str += f"\nPlayer: {player}"
            tmp_str += f"\nNb results: {len(result)}"
            tmp_str += "\n----------"

            for reslt in result:
                tmp_str += f"\n{reslt['date']}"
                tmp_str += f" - {reslt['commander']}"
                tmp_str += f" - {reslt['rank']} / {reslt['size']}"
                tmp_str += f" - {reslt['url']}" if use_url else ""

            out_str.append(tmp_str)

        with open(output, "+w", encoding="utf-8") as file:
            file.write("\n".join(out_str))


class PlayerDatabase:
    def __init__(
        self,
        directory: str = "mtgdc_decklists/decklists",
        date_from: datetime = datetime(1993, 8, 5),  # Limited Edition Alpha Release
        # date_from: datetime = datetime(2016, 11, 11),  # 20PV official date change
        date_to: datetime = datetime.now(),
    ) -> None:
        self.liste_decks = ImportDecks.from_directory(directory)
        self.liste_decks.load_decks(date_from, date_to)

        self.players_info = defaultdict(
            lambda: {"nb_top": 0, "alias": list(), "deck": defaultdict(int)}
        )

        self.player_entries = defaultdict(str)

        self._build_players_info()

    def check_aliases(self, player: str):
        players_names = list(self.players_info.keys())
        players_names = sorted(
            players_names, key=lambda x: len(x.split()), reverse=True
        )

        # Step 1: Vérifier les correspondances directes
        similarities = []
        for person2 in players_names:
            if PlayerDatabase.evaluate_similarity(player, person2):
                similarities.append(person2)

        # Step 2: Vérifier si les noms identifiés retournent d'autres résultats
        tmp_combinations = [
            (person1, person2)
            for person1 in similarities
            for person2 in players_names
            if person2 not in similarities
        ]
        for person1, person2 in tmp_combinations:
            if PlayerDatabase.evaluate_similarity(person1, person2):
                similarities.append(person2)

        return list(set(similarities))

    @staticmethod
    def evaluate_similarity(entry1, entry2):
        similarity = PlayerDatabase.calculate_similarity(entry1, entry2)
        apost = (
            ("'" in entry1 or entry2)
            or ('"' in entry1 or entry2)
            or ("(" in entry1 or entry2)
        )
        return any(
            [
                similarity > 0.85,
                apost and PlayerDatabase.same_with_alias(entry1, entry2),
            ]
        )

    @staticmethod
    def calculate_similarity(entry1, entry2):
        return 1 - textdistance.damerau_levenshtein.normalized_distance(entry1, entry2)

    @staticmethod
    def same_with_alias(entry1, entry2):
        entry1 = [
            "".join(char.lower() for char in word if char.isalpha())
            for word in entry1.split()
        ]
        entry2 = [
            "".join(char.lower() for char in word if char.isalpha())
            for word in entry2.split()
        ]

        return all(word in entry2 for word in entry1) or all(
            word in entry1 for word in entry2
        )

    def _build_players_info(self):
        for deck in self.liste_decks.decks:
            commander = DATABASE.str_command_zone(deck["commander"])
            player = deck["player"]
            self.players_info[player]["nb_top"] += 1
            self.players_info[player]["deck"][commander] += 1


class CompareLists:
    def __init__(self, decklists: list) -> None:
        self.decklists = decklists
        self.comparaison = []
        self._generate_comparison()

    def export(self, output: str = "barrins-codex-comparaison.html") -> None:
        table = "<table style='border: 1px grey double'><thead><tr><th></th>"
        for i in range(len(self.decklists)):
            table += f"<th>Cluster {i+1}</th>"
        table += "</tr></thead><tbody>"

        for i in range(len(self.decklists)):
            line = f"<tr><th>Cluster {i+1}</th>"
            for j in range(len(self.decklists)):
                line += "<td>" + self.comparaison[i][j] + "</td>"
            table += line + "</tr>"

        table += "</tbody></table>"

        with open(output, "+w", encoding="utf-8") as file:
            file.write(self.file_header)
            file.write(table)
            file.write(self.file_footer)

    @staticmethod
    def load_decks(segment: str = ".") -> None:
        files = sorted(glob.glob(os.path.join(segment, "*cluster_*")))
        for idx, file in enumerate(sorted(files)):
            with open(file, "r", encoding="utf-8") as myf:
                files[idx] = myf.read().split("\n")
        compare = CompareLists(files)
        return compare

    @property
    def file_header(self) -> str:
        return """<html>
    <header>
        <meta charset="utf-8">
        <title>Comparaison des clusters</title>
    </header>

    <body>
    <h1>Comparaison des clusters</h1>
"""

    @property
    def file_footer(self) -> str:
        d = HtmlDiff()

        style = """
body > table > tbody > tr > td {
    border: 1px grey dashed;
    vertical-align: top;
}
"""

        return """{legend}
    </body>
    <style>
    {style}
    {style2}
    </style>
    </html>
    """.format(
            legend=d._legend, style=style, style2=d._styles
        )

    def _generate_comparison(self) -> None:
        d = HtmlDiff()
        decklists = self.decklists
        comparaisons = [
            ["" for _ in range(len(decklists))] for _ in range(len(decklists))
        ]

        for i in range(len(decklists)):
            deck_i = decklists[i]
            for j in range(len(decklists)):
                if i < j:
                    comparaison = d.make_table(deck_i, decklists[j])

                    diff_lines = comparaison.splitlines()
                    modified_lines = [line for line in diff_lines if "href" in line]
                    modified_lines = (
                        self._table_part("header")
                        + "\n".join(modified_lines)
                        + self._table_part("footer")
                    )

                    comparaisons[i][j] = str(modified_lines)
                    comparaisons[j][i] = str(modified_lines)
                if i == j:
                    comparaisons[i][j] = d.make_table(deck_i, deck_i)

        self.comparaison = comparaisons

    def _table_part(self, part: str) -> str:
        if part == "header":
            return """<table class="diff" id="difflib_chg_to0__top" cellspacing="0" cellpadding="0" rules="groups" ><colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup><colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup><tbody>"""
        elif part == "footer":
            return """</tbody></table>"""
        else:
            return ""

import glob
import json
import os
import re
from datetime import datetime
from difflib import HtmlDiff


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
        date_from: datetime = datetime(1993, 8, 5),
        date_to: datetime = datetime.now(),
        **kwargs,
    ) -> None:
        size = kwargs.get("size", 0)
        commander = kwargs.get("commander", [])
        cards = kwargs.get("cards", [])

        for file in self.files:
            with open(file, "r", encoding="utf-8") as my_file:
                tournoi = json.load(my_file)

            tournoi_date = datetime.strptime(tournoi["date"], "%d/%m/%y")
            if tournoi_date < date_from:
                continue
            if tournoi_date > date_to:
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
                            "date": tournoi_date,
                            "decklist": tmp,
                            "commander": czone,
                            # "cardlist": [card for (_, card) in tmp],
                        }
                    )

    @staticmethod
    def from_directory(directory_path):
        import_decks = ImportDecks()
        import_decks.files = sorted(glob.glob(os.path.join(directory_path, "*.json")))
        return import_decks

    @property
    def decklists(self) -> list:
        return [deck["decklist"] for deck in self.decks]

    def _check(self, search_list: list, wanted: list) -> bool:
        return len(wanted) == 0 or all(
            any(clean(im).startswith(clean(wnt)) for im in search_list)
            for wnt in wanted
        )


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

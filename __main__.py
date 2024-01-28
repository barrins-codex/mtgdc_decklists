from mtgdc_carddata import CardDatabase
from mtgdc_decklists import ImportDecks

DATABASE = CardDatabase()


def control_card_names():
    liste_decks = ImportDecks.from_directory()
    liste_decks.load_decks()

    for deck in liste_decks.decks:
        if "Unknown Card" in deck["cardlist"]:
            continue

        for card_name in deck["cardlist"]:
            try:
                DATABASE.card(card_name)["type"].lower()
            except KeyError:
                print(card_name)


if __name__ == "__main__":
    control_card_names()

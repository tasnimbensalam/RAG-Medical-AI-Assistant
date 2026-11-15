"""Tests du nettoyage. À placer dans : server/tests/test_text_cleaning.py"""
from modules.text_cleaning import clean_pages, find_repeated_lines, normalize_chars


CONTENU = [
    "La bronchiolite touche surtout les nourrissons.",
    "Le virus se transmet par les mains et la toux.",
    "Il faut consulter si le bébé respire vite.",
    "La vaccination de la mère protège le nouveau-né.",
]


def make_pages():
    n = len(CONTENU)
    return [
        f"Guide de la bronchiolite\nMinistère de la Santé\n{phrase}\nVoici les recomman-\n"
        f"dations   de   prise en charge {mot}.\n\n\n\nParagraphe final {mot}.\n{i} / {n}"
        for i, (phrase, mot) in enumerate(zip(CONTENU, ["alpha", "bravo", "charlie", "delta"]), 1)
    ]


def test_normalize_chars_replaces_ligatures_and_nbsp():
    assert normalize_chars("eﬃcace : oui­") == "efficace : oui"


def test_find_repeated_lines_detects_header():
    repeated = find_repeated_lines(make_pages())
    assert "guide de la bronchiolite" in repeated
    assert "ministère de la santé" in repeated


def test_clean_pages_removes_headers_and_page_numbers():
    cleaned, stats = clean_pages(make_pages())
    assert all("Guide de la bronchiolite" not in p for p in cleaned)
    assert all("/ 4" not in p for p in cleaned)
    assert stats["lignes_entete_pied"] == 8      # 2 lignes d'en-tête x 4 pages
    assert stats["numeros_de_page"] == 4


def test_clean_pages_rejoins_hyphenated_words_and_spaces():
    cleaned, stats = clean_pages(make_pages())
    assert "recommandations de prise en charge alpha." in cleaned[0]
    assert stats["mots_recolles"] == 4
    assert "\n\n\n" not in cleaned[0]


def test_clean_pages_keeps_content_and_page_count():
    pages = make_pages()
    cleaned, stats = clean_pages(pages)
    assert len(cleaned) == len(pages)            # une page reste une page (métadonnées conservées)
    assert CONTENU[1] in cleaned[1]
    assert stats["caracteres_apres"] < stats["caracteres_avant"]


def test_short_document_keeps_its_first_lines():
    # Moins de 3 pages : on ne peut pas savoir ce qui est un en-tête, donc on ne supprime rien.
    cleaned, stats = clean_pages(["Titre\nTexte A", "Titre\nTexte B"])
    assert cleaned[0].startswith("Titre")
    assert stats.get("lignes_entete_pied", 0) == 0


def test_real_hyphens_are_kept():
    cleaned, _ = clean_pages(["Le test M-CHAT est utilisé.\nUn trouble neuro-développemental."])
    assert "M-CHAT" in cleaned[0] and "neuro-développemental" in cleaned[0]

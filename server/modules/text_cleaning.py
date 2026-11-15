"""Nettoyage du texte extrait des PDF, avant le découpage en chunks.


Quatre opérations, dans cet ordre :
  1. normaliser les caractères (espaces insécables, ligatures, caractères invisibles) ;
  2. supprimer les en-têtes et pieds de page répétés d'une page à l'autre, et les numéros de page ;
  3. recoller les mots coupés en fin de ligne (« recomman-\\ndations » -> « recommandations ») ;
  4. réduire les espaces et les lignes vides en trop.

Pourquoi : un en-tête répété sur 40 pages se retrouve dans des dizaines de chunks et fausse
la recherche ; un mot coupé en deux n'est plus retrouvé ; les espaces en trop consomment
des caractères dans des chunks de taille fixe.

clean_pages renvoie aussi des statistiques, pour pouvoir dire ce qui a été retiré.
"""
import re
import unicodedata
from collections import Counter

# Une ligne est considérée comme en-tête / pied de page si elle revient sur au moins
# cette part des pages (et sur au moins MIN_PAGES pages).
REPEAT_RATIO = 0.5
MIN_PAGES = 3
# On ne cherche les en-têtes / pieds de page que dans les premières et dernières lignes de chaque page.
EDGE_LINES = 3

_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍﻿"))  # trait d'union conditionnel, espaces de largeur nulle
_PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d{1,4}(\s*(/|sur|of)\s*\d{1,4})?\s*$", re.IGNORECASE)
_HYPHEN_BREAK = re.compile(r"([a-zà-öø-ÿ])-\n([a-zà-öø-ÿ])")


def normalize_chars(text: str) -> str:
    """Ligatures (ﬁ -> fi), espaces insécables -> espaces, suppression des caractères invisibles."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_INVISIBLE)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _key(line: str) -> str:
    """Forme de comparaison d'une ligne : minuscules, espaces réduits, chiffres remplacés par #.
    Ainsi « Page 3 / 42 » et « Page 4 / 42 » sont reconnues comme la même ligne."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line).strip().lower())


def find_repeated_lines(pages: list[str]) -> set[str]:
    """Repère les lignes qui reviennent en haut ou en bas de la plupart des pages."""
    if len(pages) < MIN_PAGES:
        return set()
    counts = Counter()
    for page in pages:
        lines = [l for l in page.split("\n") if l.strip()]
        edges = lines[:EDGE_LINES] + lines[-EDGE_LINES:]
        counts.update({_key(l) for l in edges})  # set : une ligne compte une fois par page
    threshold = max(MIN_PAGES, int(len(pages) * REPEAT_RATIO))
    return {key for key, n in counts.items() if n >= threshold and len(key) > 2}


def clean_page(text: str, repeated: set[str], stats: Counter) -> str:
    lines = text.split("\n")
    # Seules les premières et dernières lignes non vides d'une page peuvent être retirées :
    # un nombre seul au milieu d'un tableau n'est pas un numéro de page.
    non_empty = [i for i, l in enumerate(lines) if l.strip()]
    edges = set(non_empty[:EDGE_LINES] + non_empty[-EDGE_LINES:])
    kept = []
    for i, line in enumerate(lines):
        if i in edges and _PAGE_NUMBER.match(line):
            stats["numeros_de_page"] += 1
        elif i in edges and _key(line) in repeated:
            stats["lignes_entete_pied"] += 1
        else:
            kept.append(line.rstrip())
    text = "\n".join(kept)

    text, n = _HYPHEN_BREAK.subn(r"\1\2", text)
    stats["mots_recolles"] += n

    text = re.sub(r"[ \t]+", " ", text)       # plusieurs espaces -> un seul
    text = re.sub(r" ?\n ?", "\n", text)      # espaces autour des retours à la ligne
    text = re.sub(r"\n{3,}", "\n\n", text)    # au plus une ligne vide
    return text.strip()


def clean_pages(pages: list[str]) -> tuple[list[str], dict]:
    """Nettoie les pages d'UN document. Renvoie (pages nettoyées, statistiques)."""
    stats = Counter()
    pages = [normalize_chars(p or "") for p in pages]
    stats["caracteres_avant"] = sum(len(p) for p in pages)
    repeated = find_repeated_lines(pages)
    cleaned = [clean_page(p, repeated, stats) for p in pages]
    stats["caracteres_apres"] = sum(len(p) for p in cleaned)
    stats["lignes_repetees_distinctes"] = len(repeated)
    return cleaned, dict(stats)

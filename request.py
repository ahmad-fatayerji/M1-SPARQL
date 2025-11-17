import rdflib
import requests

TTL_FILE = "outTest.ttl"
LOG_FILE = "invalid_uris.txt"

# Timeout court pour éviter de bloquer sur une URI cassée
TIMEOUT = 5

def is_valid_dbpedia_uri(uri: str) -> bool:
    """Teste l'existence d'une URI DBpedia via une requête HEAD."""
    try:
        resp = requests.head(uri, allow_redirects=True, timeout=TIMEOUT)
        return resp.status_code == 200
    except requests.RequestException:
        return False

def main():
    g = rdflib.Graph()
    g.parse(TTL_FILE, format="turtle")

    # Récupérer toutes les URI DBpedia présentes dans le fichier
    dbpedia_uris = set(
        str(o)
        for s, p, o in g
        if isinstance(o, rdflib.URIRef) and str(o).startswith("http://dbpedia.org/resource/")
    ) | set(
        str(s)
        for s, p, o in g
        if isinstance(s, rdflib.URIRef) and str(s).startswith("http://dbpedia.org/resource/")
    )

    print(f"🔍 {len(dbpedia_uris)} URI DBpedia détectées à tester...")

    invalid = []

    for uri in sorted(dbpedia_uris):
        if not is_valid_dbpedia_uri(uri):
            invalid.append(uri)
            print(f"Invalide : {uri}")
        else:
            print(f"OK : {uri}")

    if invalid:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            for uri in invalid:
                f.write(uri + "\n")
        print(f"\n{len(invalid)} URI invalides enregistrées dans {LOG_FILE}")
    else:
        print("\nToutes les URI DBpedia sont valides.")

if __name__ == "__main__":
    main()

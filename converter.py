import pandas as pd
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import FOAF, XSD
from urllib.parse import quote
import os

def safe_uri_component(value: str) -> str:
    """Encode safely a string to be used inside a URI"""
    return quote(value.strip().replace(" ", "_"))

def csv_to_rdf(csv_file, output_ttl=None):
    if output_ttl is None:
        output_ttl = os.path.splitext(csv_file)[0] + ".ttl"    # Charger CSV avec séparateur ;

    df = pd.read_csv(csv_file, delimiter=";", encoding="utf-8")

    # Création graphe RDF
    g = Graph()

    # Espaces de noms
    schema = Namespace("http://schema.org/")
    nobel = Namespace("http://example.org/nobel/")

    g.bind("foaf", FOAF)
    g.bind("schema", schema)
    g.bind("nobel", nobel)

    # Parcours des lignes CSV
    for index, row in df.iterrows():
        firstname = str(row.get("Firstname", "")).strip()
        surname = str(row.get("Surname", "")).strip()
        born = str(row.get("Born", "")).strip()
        died = str(row.get("Died", "")).strip()
        year = str(row.get("Year", "")).strip()
        category = str(row.get("Category", "")).strip()

        # Encode pour URI
        firstname_enc = safe_uri_component(firstname)
        surname_enc = safe_uri_component(surname)
        year_enc = safe_uri_component(year) if year else "unknown"

        # Création des URI valides
        person_uri = URIRef(f"http://example.org/nobel/person/{firstname_enc}_{surname_enc}")
        award_uri = URIRef(f"http://example.org/nobel/award/{firstname_enc}_{surname_enc}_{year_enc}")

        # --- Personne ---
        g.add((person_uri, RDF.type, FOAF.Person))
        if firstname:
            g.add((person_uri, FOAF.givenName, Literal(firstname, datatype=XSD.string)))
        if surname:
            g.add((person_uri, FOAF.familyName, Literal(surname, datatype=XSD.string)))
        if born:
            g.add((person_uri, schema.birthDate, Literal(born, datatype=XSD.date)))
        if died:
            g.add((person_uri, schema.deathDate, Literal(died, datatype=XSD.date)))

        # --- Récompense ---
        g.add((award_uri, RDF.type, schema.Award))
        if year:
            g.add((award_uri, schema.awardDate, Literal(year, datatype=XSD.gYear)))
        if category:
            g.add((award_uri, schema.category, Literal(category, datatype=XSD.string)))

        # Lien récompense ↔ personne
        g.add((award_uri, schema.recipient, person_uri))

    
    g.serialize(destination=output_ttl, format="turtle")

    print(f"Fichier RDF généré : {output_ttl}")


# Exemple d’exécution
csv_file = "./nobel-prize-laureates.csv"
output_ttl = "nobel.ttl"
csv_to_rdf(csv_file, output_ttl)

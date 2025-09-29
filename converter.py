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
        output_ttl = os.path.splitext(csv_file)[0] + ".ttl"

    # Charger CSV avec séparateur ;
    df = pd.read_csv(csv_file, delimiter=";", encoding="utf-8")

    # Création graphe RDF
    g = Graph()

    # Espaces de noms
    schema = Namespace("http://schema.org/")
    nobel = Namespace("http://example.org/nobel/")
    place_ns = Namespace("http://example.org/nobel/place/")
    org_ns = Namespace("http://example.org/nobel/organization/")

    g.bind("foaf", FOAF)
    g.bind("schema", schema)
    g.bind("nobel", nobel)
    g.bind("place", place_ns)
    g.bind("organization", org_ns)

    # Parcours des lignes CSV
    for index, row in df.iterrows():
        # --- 1. Extraction de toutes les données du CSV ---
        firstname = str(row.get("Firstname", "")).strip()
        surname = str(row.get("Surname", "")).strip()
        born = str(row.get("Born", "")).strip()
        died = str(row.get("Died", "")).strip()
        year = str(row.get("Year", "")).strip()
        category = str(row.get("Category", "")).strip()
        
        # Nouvelles données ajoutées
        motivation = str(row.get("Motivation", "")).strip().replace('"', '')
        gender = str(row.get("Gender", "")).strip()
        
        # Lieu de Naissance
        born_country = str(row.get("Born country", "")).strip()
        born_city = str(row.get("Born city", "")).strip()
        
        # Lieu de Décès
        died_country = str(row.get("Died country", "")).strip()
        died_city = str(row.get("Died city", "")).strip()
        
        # Affiliation
        org_name = str(row.get("Organization name", "")).strip()
        org_city = str(row.get("Organization city", "")).strip()
        org_country = str(row.get("Organization country", "")).strip()
        
        
        # --- 2. Encodage pour URI ---
        # S'assurer que nous avons un nom pour créer une URI
        if not firstname and not surname:
            continue
            
        name_for_uri = f"{firstname}_{surname}" if firstname and surname else (firstname or surname)
        
        person_name_enc = safe_uri_component(name_for_uri)
        year_enc = safe_uri_component(year) if year else "unknown"

        # Création des URI valides
        person_uri = URIRef(nobel + f"person/{person_name_enc}")
        award_uri = URIRef(nobel + f"award/{person_name_enc}_{year_enc}_{category}")

        # --- 3. Construction des triples RDF ---
        
        # --- Personne (Laureate) ---
        g.add((person_uri, RDF.type, FOAF.Person))
        
        if firstname:
            g.add((person_uri, FOAF.givenName, Literal(firstname, datatype=XSD.string)))
        if surname:
            g.add((person_uri, FOAF.familyName, Literal(surname, datatype=XSD.string)))
        if born:
            # On utilise XSD.date pour les dates de naissance, même si elles sont imprécises parfois dans le CSV
            g.add((person_uri, schema.birthDate, Literal(born, datatype=XSD.date)))
        if died:
            g.add((person_uri, schema.deathDate, Literal(died, datatype=XSD.date)))
        if gender:
            g.add((person_uri, schema.gender, Literal(gender, datatype=XSD.string)))

        
        # --- Lieu de Naissance (schema:Place) ---
        if born_city or born_country:
            place_id = safe_uri_component(f"Born_{born_city}_{born_country}")
            place_uri = URIRef(place_ns + place_id)
            
            g.add((person_uri, schema.birthPlace, place_uri))
            g.add((place_uri, RDF.type, schema.Place))
            if born_city:
                g.add((place_uri, schema.addressLocality, Literal(born_city)))
            if born_country:
                g.add((place_uri, schema.addressCountry, Literal(born_country)))

        # --- Lieu de Décès (schema:Place) ---
        if died_city or died_country:
            place_id = safe_uri_component(f"Died_{died_city}_{died_country}")
            place_uri = URIRef(place_ns + place_id)
            
            g.add((person_uri, schema.deathPlace, place_uri))
            g.add((place_uri, RDF.type, schema.Place))
            if died_city:
                g.add((place_uri, schema.addressLocality, Literal(died_city)))
            if died_country:
                g.add((place_uri, schema.addressCountry, Literal(died_country)))


        # --- Récompense (Award) ---
        g.add((award_uri, RDF.type, schema.Award))
        
        if year:
            g.add((award_uri, schema.awardDate, Literal(year, datatype=XSD.gYear)))
        if category:
            g.add((award_uri, schema.category, Literal(category, datatype=XSD.string)))
        if motivation:
            # Ajout de la motivation
            g.add((award_uri, schema.description, Literal(motivation, lang='en')))
            
        # Lien récompense ↔ personne
        g.add((award_uri, schema.recipient, person_uri))
        
        
        # --- Affiliation (Organization) ---
        if org_name:
            org_id = safe_uri_component(org_name)
            org_uri = URIRef(org_ns + org_id)
            
            # Lien personne ↔ organisation
            g.add((person_uri, schema.affiliation, org_uri)) 
            
            g.add((org_uri, RDF.type, schema.Organization))
            g.add((org_uri, FOAF.name, Literal(org_name)))
            
            # Ajout du lieu de l'organisation
            if org_city or org_country:
                org_place_id = safe_uri_component(f"OrgPlace_{org_city}_{org_country}")
                org_place_uri = URIRef(place_ns + org_place_id)
                
                g.add((org_uri, schema.location, org_place_uri))
                g.add((org_place_uri, RDF.type, schema.Place))
                if org_city:
                    g.add((org_place_uri, schema.addressLocality, Literal(org_city)))
                if org_country:
                    g.add((org_place_uri, schema.addressCountry, Literal(org_country)))


    # Sérialisation et écriture du graphe en TTL
    g.serialize(destination=output_ttl, format="turtle")
    
    print(f"Conversion terminée. Fichier TTL sauvegardé : {output_ttl}")

if __name__ == '__main__':
    # REMPLACER 'nobel-prize-laureates.csv' par le nom de votre fichier si nécessaire
    csv_to_rdf('nobel-prize-laureates.csv', 'nobel_complete.ttl')
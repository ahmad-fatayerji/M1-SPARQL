import pandas as pd
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import FOAF, XSD
from urllib.parse import quote
import os
import re

# --- Mapping manuel pour les pays avec noms historiques / abréviations ---
COUNTRY_URI_MAP = {
    "U.S.A.": "United_States",
    "USA": "United_States",
    "U. S. A.": "United_States",
    "United States of America": "United_States",
    "Deutschland": "Germany",
    "UK": "United_Kingdom",
    "U.K.": "United_Kingdom",
    "Russian Federation": "Russia",
    "USSR": "Russia",
    "USSR (now Russia)": "Russia",
    "Russian Empire (now Poland)": "Poland",
    "Russian Empire (now Lithuania)": "Lithuania",
    "the Netherlands": "Netherlands",
    "Austria-Hungary (now Austria)": "Austria",
    "Austria-Hungary (now Bosnia and Herzegovina)": "Bosnia_and_Herzegovina",
    "Austria-Hungary (now Croatia)": "Croatia",
    "Austria-Hungary (now Czech Republic)": "Czech_Republic",
    "Austria-Hungary (now Hungary)": "Hungary",
    "Austria-Hungary (now Poland)": "Poland",
    "Austria-Hungary (now Slovenia)": "Slovenia",
    "Austria-Hungary (now Ukraine)": "Ukraine",
    "Austrian Empire (now Austria)": "Austria",
    "Austrian Empire (now Czech Republic)": "Czech_Republic",
    "Austrian Empire (now Italy)": "Italy",
    "Bavaria (now Germany)": "Germany",
    "Belgian Congo (now Democratic Republic of the Congo)": "Democratic_Republic_of_the_Congo",
    "Bosnia (now Bosnia and Herzegovina)": "Bosnia_and_Herzegovina",
    "British India (now Bangladesh)": "Bangladesh",
    "British India (now India)": "India",
    "British Mandate of Palestine (now Israel)": "Israel",
    "British Protectorate of Palestine (now Israel)": "Israel",
    "British West Indies (now Saint Lucia)": "Saint_Lucia",
    "Burma (now Myanmar)": "Myanmar",
    "Czechoslovakia (now Czech Republic)": "Czech_Republic",
    "East Friesland (now Germany)": "Germany",
    "East Germany (now Germany)": "Germany",
    "French Algeria (now Algeria)": "Algeria",
    "French protectorate of Tunisia (now Tunisia)": "Tunisia",
    "German-occupied Poland (now Poland)": "Poland",
    "Germany (now France)": "France",
    "Germany (now Poland)": "Poland",
    "Germany (now Russia)": "Russia",
    "Gold Coast (now Ghana)": "Ghana",
    "Hungary (now Slovakia)": "Slovakia",
    "India (now Pakistan)": "Pakistan",
    "Korea (now South Korea)": "South_Korea",
    "Ottoman Empire (now North Macedonia)": "North_Macedonia",
    "Ottoman Empire (now Turkey)": "Turkey",
    "Persia (now Iran)": "Iran",
    "Poland (now Belarus)": "Belarus",
    "Poland (now Lithuania)": "Lithuania",
    "Poland (now Ukraine)": "Ukraine",
    "Prussia (now Germany)": "Germany",
    "Prussia (now Poland)": "Poland",
    "Prussia (now Russia)": "Russia",
    "Russian Empire (now Azerbaijan)": "Azerbaijan",
    "Russian Empire (now Belarus)": "Belarus",
    "Russian Empire (now Finland)": "Finland",
    "Russian Empire (now Latvia)": "Latvia",
    "Russian Empire (now Russia)": "Russia",
    "Russian Empire (now Ukraine)": "Ukraine",
    "Southern Rhodesia (now Zimbabwe)": "Zimbabwe",
    "Tibet (now China)": "China",
    "Tuscany (now Italy)": "Italy",
    "USSR (now Belarus)": "Belarus",
    "West Germany (now Germany)": "Germany",
    "Yugoslavia (now Serbia)": "Serbia"
}

CITY_URI_MAP = {
    "Aberdeen WA": "Aberdeen,_Washington",
    "Ann Arbor MI": "Ann_Arbor,_Michigan",
    "Akron OH": "Akron,_Ohio",
    "Albuquerque NM": "Albuquerque,_New_Mexico",
    "Amherst NS": "Amherst,_Nova_Scotia",
    "Baltimore MD": "Baltimore,_Maryland",
    "Berkeley CA": "Berkeley,_California",
    "Boulder CO": "Boulder,_Colorado",
    "Chicago IL": "Chicago",
    "Cologne": "Cologne", 
    "Stanford CA": "Stanford,_California",
    "New Haven CT": "New_Haven,_Connecticut",
    "Pasadena CA": "Pasadena,_California",
    "Palo Alto CA": "Palo_Alto,_California",
    "Cambridge MA": "Cambridge,_Massachusetts",
    "Princeton NJ": "Princeton,_New_Jersey",
    "Berkeley CA": "Berkeley,_California",
    "New York NY": "New_York_City",
    "Los Angeles CA": "Los_Angeles",
    "San Francisco CA": "San_Francisco",
    "the Hague": "The_Hague"

}

# --- Fonctions utilitaires ---
def safe_uri_component(value: str) -> str:
    return quote(value.strip().replace(" ", "_"))

def normalize_country_to_uri(country: str, dbpedia_res: Namespace, log_file="unmapped_countries.txt") -> URIRef:
    if not country or pd.isna(country):
        return None

    c = country.strip().replace(".", "").replace("  ", " ")

    if c in COUNTRY_URI_MAP:
        return URIRef(dbpedia_res + COUNTRY_URI_MAP[c])

    candidate = safe_uri_component(c)
    if candidate:
        return URIRef(dbpedia_res + candidate)
    
    return None


def normalize_city_to_uri(city: str, dbpedia_res: Namespace, log_file="unmapped_cities.txt") -> URIRef:
    if not city or pd.isna(city) or str(city).lower() == "nan":
        return None

    c = city.strip()

    # Map manuelle en priorité
    if c in CITY_URI_MAP:
        return URIRef(dbpedia_res + CITY_URI_MAP[c])

    # Fallback automatique
    candidate = safe_uri_component(c)
    if candidate:
        # Log car URI potentiellement invalide
        return URIRef(dbpedia_res + candidate)
    return None



def csv_to_rdf(csv_file, output_ttl=None):
    if output_ttl is None:
        output_ttl = os.path.splitext(csv_file)[0] + ".ttl"

    df = pd.read_csv(csv_file, delimiter=";", encoding="utf-8")
    g = Graph()

    # --- Namespaces ---
    schema = Namespace("http://schema.org/")
    dbo = Namespace("http://dbpedia.org/ontology/")
    dbr = Namespace("http://dbpedia.org/resource/")
    nobel = Namespace("http://example.org/nobel/")
    place_ns = Namespace("http://example.org/nobel/place/")
    org_ns = Namespace("http://example.org/nobel/organization/")

    g.bind("foaf", FOAF)
    g.bind("dbo", dbo)
    g.bind("dbr", dbr)
    g.bind("nobel", nobel)
    g.bind("place", place_ns)
    g.bind("organization", org_ns)
    g.bind("schema", schema)

    for index, row in df.iterrows():
        firstname = str(row.get("Firstname", "")).strip()
        surname = str(row.get("Surname", "")).strip()
        born = str(row.get("Born", "")).strip()
        died = str(row.get("Died", "")).strip()
        year = str(row.get("Year", "")).strip()
        category = str(row.get("Category", "")).strip()
        motivation = str(row.get("Motivation", "")).strip().replace('"', '')
        gender = str(row.get("Gender", "")).strip()

        born_country = str(row.get("Born country", "")).strip()
        born_city = str(row.get("Born city", "")).strip()
        died_country = str(row.get("Died country", "")).strip()
        died_city = str(row.get("Died city", "")).strip()
        org_name = str(row.get("Organization name", "")).strip()
        org_city = str(row.get("Organization city", "")).strip()
        org_country = str(row.get("Organization country", "")).strip()

        has_name = bool(firstname or surname)
        if not has_name:
            continue

        laureate_is_org = (gender or "").strip().lower() == "org"
        display_name = firstname if (laureate_is_org and firstname) else (
            f"{firstname} {surname}".strip() if (firstname and surname) else (firstname or surname)
        )
        name_for_uri = f"{firstname}_{surname}" if (firstname and surname) else (firstname or surname)
        name_enc = safe_uri_component(name_for_uri)
        year_enc = safe_uri_component(year) if year else "unknown"
        category_enc = safe_uri_component(category) if category else "unknown"

        if laureate_is_org:
            laureate_uri = URIRef(org_ns + name_enc)
        else:
            laureate_uri = URIRef(nobel + f"person/{name_enc}")

        award_uri = URIRef(nobel + f"award/{name_enc}_{year_enc}_{category_enc}")

        # --- Lauréat ---
        if laureate_is_org:
            g.add((laureate_uri, RDF.type, schema.Organization))
            if display_name:
                g.add((laureate_uri, FOAF.name, Literal(display_name, datatype=XSD.string)))
        else:
            g.add((laureate_uri, RDF.type, FOAF.Person))
            if firstname:
                g.add((laureate_uri, FOAF.givenName, Literal(firstname, datatype=XSD.string)))
            if surname:
                g.add((laureate_uri, FOAF.familyName, Literal(surname, datatype=XSD.string)))
            if born:
                g.add((laureate_uri, schema.birthDate, Literal(born, datatype=XSD.date)))
            if died:
                g.add((laureate_uri, schema.deathDate, Literal(died, datatype=XSD.date)))
            if gender and gender.strip().lower() in {"male", "female"}:
                g.add((laureate_uri, schema.gender, Literal(gender, datatype=XSD.string)))

        # --- Lieu de Naissance ---
        if (born_city or born_country) and not laureate_is_org:
            place_id = safe_uri_component(f"{born_city}_{born_country}")
            place_uri = URIRef(place_ns + place_id)

            g.add((laureate_uri, schema.birthPlace, place_uri))
            g.add((place_uri, RDF.type, schema.Place))

            if born_city:
                city_uri = normalize_city_to_uri(born_city, dbr)
                if city_uri:
                    g.add((place_uri, dbo.city, city_uri))

            if born_country:
                country_uri = normalize_country_to_uri(born_country, dbr)
                if country_uri:
                    g.add((place_uri, dbo.country, country_uri))

        # --- Lieu de Décès ---
        if (died_city or died_country) and not laureate_is_org:
            place_id = safe_uri_component(f"{died_city}_{died_country}")
            place_uri = URIRef(place_ns + place_id)

            g.add((laureate_uri, schema.deathPlace, place_uri))
            g.add((place_uri, RDF.type, schema.Place))

            if died_city:
                city_uri = normalize_city_to_uri(died_city, dbr)
                if city_uri:
                    g.add((place_uri, dbo.city, city_uri))

            if died_country:
                country_uri = normalize_country_to_uri(died_country, dbr)
                if country_uri:
                    g.add((place_uri, dbo.country, country_uri))

        # --- Récompense ---
        g.add((award_uri, RDF.type, schema.Award))
        if year:
            g.add((award_uri, schema.awardDate, Literal(year, datatype=XSD.gYear)))
        if category:
            g.add((award_uri, schema.category, Literal(category, datatype=XSD.string)))
        if motivation:
            g.add((award_uri, schema.description, Literal(motivation, lang='en')))
        g.add((award_uri, schema.recipient, laureate_uri))

        # --- Organisation ---
        if org_name and not laureate_is_org:
            org_id = safe_uri_component(org_name)
            org_uri = URIRef(org_ns + org_id)

            g.add((laureate_uri, schema.affiliation, org_uri))
            g.add((org_uri, RDF.type, schema.Organization))
            g.add((org_uri, FOAF.name, Literal(org_name)))

            if org_city or org_country:
                org_place_id = safe_uri_component(f"{org_city}_{org_country}")
                org_place_uri = URIRef(place_ns + org_place_id)

                g.add((org_uri, schema.location, org_place_uri))
                g.add((org_place_uri, RDF.type, schema.Place))

                if org_city:
                    city_uri = normalize_city_to_uri(org_city, dbr)
                    if city_uri:
                        g.add((org_place_uri, dbo.city, city_uri))

                if org_country:
                    country_uri = normalize_country_to_uri(org_country, dbr)
                    if country_uri:
                        g.add((org_place_uri, dbo.country, country_uri))

    g.serialize(destination=output_ttl, format="turtle")
    print(f"Conversion terminée. Fichier TTL sauvegardé : {output_ttl}")

if __name__ == '__main__':
    csv_to_rdf('nobel-prize-laureates.csv', 'out.ttl')
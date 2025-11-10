import os
from urllib.parse import quote

import pandas as pd
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, XSD

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
    "Yugoslavia (now Serbia)": "Serbia",
    "Württemberg (now Germany)": "Germany",
    "Schleswig (now Germany)": "Germany",
    "Mecklenburg (now Germany)": "Germany",
    "Java Dutch East Indies (now Indonesia)": "Indonesia",
    "Hesse-Kassel (now Germany)": "Germany",
    "Crete (now Greece)": "Greece",
    "Free City of Danzig (now Poland)": "Poland",
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
    "New York NY": "New_York_City",
    "Los Angeles CA": "Los_Angeles",
    "San Francisco CA": "San_Francisco",
    "the Hague": "The_Hague",
    "Waltersdorf (now Niegoslawice)": "Niegoslawice",
    # Non finis car trop de villes dans le fichier
}


# --- Fonctions utilitaires ---
def safe_uri_component(value: str) -> str:
    return quote(value.strip().replace(" ", "_"))


def normalize_text(value) -> str:
    if not value or pd.isna(value):
        return ""
    return str(value).strip()


def normalize_country_text(value) -> str:
    return normalize_text(value).replace(".", "").replace("  ", " ")


def normalize_country_to_uri(country: str, dbpedia_res: Namespace) -> URIRef:
    c = normalize_country_text(country)
    if not c:
        return None
    if c in COUNTRY_URI_MAP:
        return URIRef(dbpedia_res + COUNTRY_URI_MAP[c])
    return URIRef(dbpedia_res + safe_uri_component(c))


def normalize_city_to_uri(city: str, dbpedia_res: Namespace) -> URIRef:
    c = normalize_text(city)
    if not c:
        return None
    if c in CITY_URI_MAP:
        return URIRef(dbpedia_res + CITY_URI_MAP[c])
    return URIRef(dbpedia_res + safe_uri_component(c))


# --- Construction des URI ---
def create_laureate_uri(row, nobel_ns, org_ns):
    firstname = normalize_text(row.get("Firstname"))
    surname = normalize_text(row.get("Surname"))
    gender = normalize_text(row.get("Gender")).lower()

    has_name = bool(firstname or surname)
    if not has_name:
        return None, False, ""

    is_org = gender == "org"
    display_name = (
        firstname
        if is_org and firstname
        else (
            f"{firstname} {surname}".strip()
            if firstname and surname
            else (firstname or surname)
        )
    )

    name_for_uri = (
        f"{firstname}_{surname}" if firstname and surname else (firstname or surname)
    )
    name_enc = safe_uri_component(name_for_uri)

    if is_org:
        return URIRef(org_ns + name_enc), True, display_name
    return URIRef(nobel_ns + f"person/{name_enc}"), False, display_name


# --- Ajout des triplets RDF ---
def add_laureate_triples(g, laureate_uri, row, is_org, schema):
    firstname = normalize_text(row.get("Firstname"))
    surname = normalize_text(row.get("Surname"))
    born = normalize_text(row.get("Born"))
    died = normalize_text(row.get("Died"))
    gender = normalize_text(row.get("Gender"))

    if is_org:
        g.add((laureate_uri, RDF.type, schema.Organization))
        if firstname or surname:
            g.add(
                (
                    laureate_uri,
                    FOAF.name,
                    Literal(firstname or surname, datatype=XSD.string),
                )
            )
    else:
        g.add((laureate_uri, RDF.type, FOAF.Person))
        if firstname:
            g.add(
                (laureate_uri, FOAF.givenName, Literal(firstname, datatype=XSD.string))
            )
        if surname:
            g.add(
                (laureate_uri, FOAF.familyName, Literal(surname, datatype=XSD.string))
            )
        if born:
            g.add((laureate_uri, schema.birthDate, Literal(born, datatype=XSD.date)))
        if died:
            g.add((laureate_uri, schema.deathDate, Literal(died, datatype=XSD.date)))
        if gender.lower() in {"male", "female"}:
            g.add((laureate_uri, schema.gender, Literal(gender, datatype=XSD.string)))


def add_place_triples(
    g, subject_uri, city, country, predicate, place_ns, dbo, dbr, schema
):
    if not city and not country:
        return

    place_id = safe_uri_component(f"{city}_{country}")
    place_uri = URIRef(place_ns + place_id)
    g.add((subject_uri, predicate, place_uri))
    g.add((place_uri, RDF.type, schema.Place))
    g.add((place_uri, RDFS.label, Literal(country, lang="en"))) # country label

    if city:
        city_uri = normalize_city_to_uri(city, dbr)
        if city_uri:
            g.add((place_uri, dbo.city, city_uri))
    if country:
        country_uri = normalize_country_to_uri(country, dbr)
        if country_uri:
            g.add((place_uri, dbo.country, country_uri))
            


def add_award_triples(g, laureate_uri, row, nobel_ns, schema):
    year = normalize_text(row.get("Year")) or "unknown"
    category = normalize_text(row.get("Category")) or "unknown"
    motivation = normalize_text(row.get("Motivation")).replace('"', "") or "unknown"

    year_enc = safe_uri_component(year)
    category_enc = safe_uri_component(category)
    name_for_uri = safe_uri_component(
        f"{normalize_text(row.get('Firstname'))}_{normalize_text(row.get('Surname'))}".strip(
            "_"
        )
        or "unknown"
    )

    award_uri = URIRef(nobel_ns + f"award/{name_for_uri}_{year_enc}_{category_enc}")
    g.add((award_uri, RDF.type, schema.Award))
    if year and year != "unknown":
        g.add((award_uri, schema.awardDate, Literal(year, datatype=XSD.gYear)))
    if category and category != "unknown":
        g.add((award_uri, schema.category, Literal(category, datatype=XSD.string)))
    if motivation:
        g.add((award_uri, schema.description, Literal(motivation, lang="en")))
    g.add((award_uri, schema.recipient, laureate_uri))


def add_organization_triples(g, laureate_uri, row, org_ns, place_ns, dbo, dbr, schema):
    org_name = normalize_text(row.get("Organization name"))
    org_city = normalize_text(row.get("Organization city"))
    org_country = normalize_country_text(row.get("Organization country"))

    if not org_name:
        return

    org_id = safe_uri_component(org_name)
    org_uri = URIRef(org_ns + org_id)
    g.add((laureate_uri, schema.affiliation, org_uri))
    g.add((org_uri, RDF.type, schema.Organization))
    g.add((org_uri, FOAF.name, Literal(org_name)))

    if org_city or org_country:
        add_place_triples(
            g,
            org_uri,
            org_city,
            org_country,
            schema.location,
            place_ns,
            dbo,
            dbr,
            schema,
        )


# --- Fonction principale ---
def csv_to_rdf(csv_file, output_ttl=None):
    if output_ttl is None:
        output_ttl = os.path.splitext(csv_file)[0] + ".ttl"

    df = pd.read_csv(csv_file, delimiter=";", encoding="utf-8")
    g = Graph()

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

    for _, row in df.iterrows():
        laureate_uri, is_org, _ = create_laureate_uri(row, nobel, org_ns)
        if not laureate_uri:
            continue

        add_laureate_triples(g, laureate_uri, row, is_org, schema)
        add_award_triples(g, laureate_uri, row, nobel, schema)

        if not is_org:
            add_place_triples(
                g,
                laureate_uri,
                normalize_text(row.get("Born city")),
                normalize_country_text(row.get("Born country")),
                schema.birthPlace,
                place_ns,
                dbo,
                dbr,
                schema,
            )
            add_place_triples(
                g,
                laureate_uri,
                normalize_text(row.get("Died city")),
                normalize_country_text(row.get("Died country")),
                schema.deathPlace,
                place_ns,
                dbo,
                dbr,
                schema,
            )
            add_organization_triples(
                g, laureate_uri, row, org_ns, place_ns, dbo, dbr, schema
            )

    g.serialize(destination=output_ttl, format="turtle")
    print(f"Conversion terminée. Fichier TTL sauvegardé : {output_ttl}")


if __name__ == "__main__":
    csv_to_rdf("nobel-prize-laureates.csv", "out.ttl")

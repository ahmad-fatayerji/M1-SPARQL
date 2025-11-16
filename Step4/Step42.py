from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, OWL, FOAF
import requests
import time
import re

SCHEMA = Namespace("http://schema.org/")
DBR = Namespace("http://dbpedia.org/resource/")

def check_dbpedia_exists(resource_name):
    dbpedia_uri = f"http://dbpedia.org/resource/{resource_name}"
    try:
        r = requests.head(dbpedia_uri, timeout=10, allow_redirects=True)
        return dbpedia_uri if r.status_code == 200 else None
    except:
        return None

def get_wikidata_from_dbpedia_sparql(dbpedia_resource_name):
    sparql_endpoint = "https://dbpedia.org/sparql"
    query = f"""
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX dbr: <http://dbpedia.org/resource/>
    SELECT ?wikidata WHERE {{
        dbr:{dbpedia_resource_name} owl:sameAs ?wikidata .
        FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
    }}
    LIMIT 1
    """
    try:
        r = requests.get(
            sparql_endpoint,
            params={'query': query, 'format': 'json'},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=15
        )
        if r.status_code == 200:
            results = r.json()
            bindings = results.get('results', {}).get('bindings', [])
            if bindings:
                return bindings[0]['wikidata']['value']
        return None
    except:
        return None

def get_wikidata_from_dbpedia_page(dbpedia_resource_name):
    rdf_url = f"http://dbpedia.org/data/{dbpedia_resource_name}.ttl"
    try:
        r = requests.get(rdf_url, timeout=15)
        if r.status_code == 200:
            temp_graph = Graph()
            temp_graph.parse(data=r.text, format="turtle")
            dbpedia_uri = URIRef(f"http://dbpedia.org/resource/{dbpedia_resource_name}")
            for _, _, o in temp_graph.triples((dbpedia_uri, OWL.sameAs, None)):
                uri_str = str(o)
                if "wikidata.org/entity/" in uri_str:
                    return uri_str
        return None
    except:
        return None

def get_wikidata_combined(dbpedia_resource_name):
    wikidata = get_wikidata_from_dbpedia_sparql(dbpedia_resource_name)
    if wikidata:
        return wikidata
    wikidata = get_wikidata_from_dbpedia_page(dbpedia_resource_name)
    return wikidata

def generate_organization_variations(org_name, location=None):
    variations = set()
    base_name = org_name.replace(" ", "_")
    variations.add(base_name)

    match = re.match(r'(.+?)\s+University$', org_name, re.IGNORECASE)
    if match:
        city_name = match.group(1).strip()
        variations.add(f"University_of_{city_name}".replace(" ", "_"))

    match = re.match(r'(.+?)\s+Institute', org_name, re.IGNORECASE)
    if match:
        name_part = match.group(1).strip()
        variations.add(f"{name_part}_Institute".replace(" ", "_"))
        if "technology" in org_name.lower():
            variations.add(f"{name_part}_Institute_of_Technology".replace(" ", "_"))

    if "School of Medicine" in org_name:
        simplified = org_name.replace("School of Medicine", "").strip()
        if simplified:
            variations.add(simplified.replace(" ", "_"))
            variations.add(f"{simplified}_School_of_Medicine".replace(" ", "_"))

    abbr_map = {
        "MIT": ["MIT", "Massachusetts_Institute_of_Technology"],
        "CalTech": ["California_Institute_of_Technology", "Caltech"],
        "UCLA": ["UCLA", "University_of_California,_Los_Angeles"],
        "NYU": ["NYU", "New_York_University"],
    }
    org_name_clean = org_name.replace(" ", "")
    if org_name_clean in abbr_map:
        variations.update(abbr_map[org_name_clean])

    if location:
        location_clean = location.replace(" ", "_")
        if "university" in org_name.lower():
            variations.add(f"University_of_{location_clean}")
        if "institute" in org_name.lower():
            variations.add(f"{location_clean}_Institute")

    variations = {v.replace("__", "_").replace(" ", "_").strip("_") for v in variations}

    variations_list = [base_name] if base_name in variations else []
    variations_list.extend([v for v in variations if v != base_name])
    return variations_list

def find_organization_on_dbpedia(org_name, location=None):
    variations = generate_organization_variations(org_name, location)
    for variation in variations:
        uri = check_dbpedia_exists(variation)
        if uri:
            return uri, variation
    return None, None

g = Graph()
g.parse("out_enriched.ttl")
output_file = "out_enriched_orgs.ttl"

organizations = []
for s in g.subjects(RDF.type, None):
    types = list(g.objects(s, RDF.type))
    is_org = any("organization" in str(t).lower() or "organisation" in str(t).lower() for t in types)

    if is_org:
        name = g.value(s, FOAF.name) or g.value(s, SCHEMA.name)
        location = g.value(s, SCHEMA.location)
        if name:
            organizations.append((s, str(name), str(location) if location else None))

for org_uri, org_name, location in organizations:
    dbpedia_uri, found_variation = find_organization_on_dbpedia(org_name, location)

    if dbpedia_uri:
        for old_link in g.objects(org_uri, OWL.sameAs):
            g.remove((org_uri, OWL.sameAs, old_link))
        g.add((org_uri, OWL.sameAs, URIRef(dbpedia_uri)))

        wikidata_uri = get_wikidata_combined(found_variation)
        if wikidata_uri:
            g.add((org_uri, OWL.sameAs, URIRef(wikidata_uri)))

        time.sleep(0.8)

    time.sleep(0.3)

g.serialize(output_file, format="turtle")

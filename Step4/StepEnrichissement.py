from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, FOAF
import requests, time, re
from urllib.parse import quote
from datetime import datetime

SCHEMA = Namespace("http://schema.org/")
DBO = Namespace("http://dbpedia.org/ontology/")
DBR = Namespace("http://dbpedia.org/resource/")

# URI ENCODING
def encode_dbpedia_uri(name):
    return quote(name, safe='_,')  # évite les apostrophes cassées

def sanitize(uri):
    if "dbpedia.org/resource/" in uri:
        name = uri.split("resource/")[-1]
        return URIRef("http://dbpedia.org/resource/" + encode_dbpedia_uri(name))
    return URIRef(uri)


# CHECK DBPEDIA
def dbpedia_exists(name):
    try:
        encoded = encode_dbpedia_uri(name)
        url = f"http://dbpedia.org/resource/{encoded}"
        r = requests.head(url, timeout=8)
        return url if r.status_code == 200 else None
    except:
        return None

# GET WIKIDATA
def wikidata_from_sparql(name):
    try:
        encoded = encode_dbpedia_uri(name)
        q = f"""
        SELECT ?wd WHERE {{
            <http://dbpedia.org/resource/{encoded}> owl:sameAs ?wd .
            FILTER(STRSTARTS(STR(?wd),"http://www.wikidata.org/entity/"))
        }} LIMIT 1
        """
        r = requests.get("https://dbpedia.org/sparql",
                         params={'query': q, 'format': 'json'},
                         timeout=10)
        b = r.json().get("results", {}).get("bindings", [])
        return b[0]["wd"]["value"] if b else None
    except:
        return None

def wikidata_from_rdf(name):
    try:
        encoded = encode_dbpedia_uri(name)
        url = f"http://dbpedia.org/data/{encoded}.ttl"
        g = Graph()
        g.parse(url, format="turtle")
        s = URIRef(f"http://dbpedia.org/resource/{encoded}")
        for _, _, o in g.triples((s, OWL.sameAs, None)):
            if "wikidata.org/entity/" in str(o):
                return str(o)
        return None
    except:
        return None

def wikidata(name):
    return wikidata_from_sparql(name) or wikidata_from_rdf(name)


# LINK ADDER
def add_sameas(g, s, uri):
    try:
        g.add((s, OWL.sameAs, sanitize(uri)))
        return True
    except Exception as e:
        print("   ✗ erreur ajout sameAs:", e)
        return False


def org_variants(name):
    base = name.replace(" ", "_")
    out = {base}

    if "University" in name:
        out.add(name.replace("University", "").strip().replace(" ", "_"))
        out.add("University_of_" + name.replace("University", "").strip().replace(" ", "_"))

    if "Institute" in name:
        out.add(name.replace(" ", "_"))
        out.add(name.replace("Institute", "Institute_of_Technology").replace(" ", "_"))

    # Nettoyage 
    return {v.strip("_").replace("__", "_") for v in out}


g = Graph()
g.parse("out_enriched.ttl")

def extract_entities(g, rdf_type):
    return [
        s for s in g.subjects(RDF.type, rdf_type)
    ]

orgs = extract_entities(g, None) 
places = extract_entities(g, SCHEMA.Place)


# ORGANIZATIONS
for s in orgs:
    name = g.value(s, FOAF.name) or g.value(s, SCHEMA.name)
    if not name:
        continue

    name = str(name)

    # skip if DBpedia exists already
    if any("dbpedia.org" in str(o) for o in g.objects(s, OWL.sameAs)):
        continue

    # try variations
    for v in org_variants(name):
        dbp = dbpedia_exists(v)
        if dbp:
            print(f"✓ DBpedia org trouvée pour {name} : {dbp}")
            add_sameas(g, s, dbp)
            wd = wikidata(v)
            if wd:
                add_sameas(g, s, wd)
            break


# PLACES
for s in places:
    # skip if DBpedia present
    if any("dbpedia.org" in str(o) for o in g.objects(s, OWL.sameAs)):
        continue

    city = g.value(s, DBO.city)
    country = g.value(s, DBO.country)
    candidate = city or country
    if not candidate:
        continue

    name = str(candidate).split("/")[-1]
    if dbpedia_exists(name):
        add_sameas(g, s, str(candidate))
        wd = wikidata(name)
        if wd:
            add_sameas(g, s, wd)


g.serialize("out_enriched_complete.ttl", format="turtle")
print("Fichier ttl terminé")

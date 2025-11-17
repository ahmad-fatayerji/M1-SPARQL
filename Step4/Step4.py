from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, OWL, FOAF
import requests
import time
import re

DBR = Namespace("http://dbpedia.org/resource/")
DBO = Namespace("http://dbpedia.org/ontology/")
WD = Namespace("http://www.wikidata.org/entity/")

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

def format_name_for_dbpedia(given_name, family_name):
    full_name = f"{given_name}_{family_name}"
    return full_name.replace(" ", "_")

g = Graph()
g.parse("../out.ttl")

persons = []
for s in g.subjects(RDF.type, FOAF.Person):
    given = g.value(s, FOAF.givenName)
    family = g.value(s, FOAF.familyName)
    if given and family:
        persons.append((s, str(given), str(family)))

for person_uri, given_name, family_name in persons:
    dbpedia_name = format_name_for_dbpedia(given_name, family_name)
    dbpedia_uri = check_dbpedia_exists(dbpedia_name)

    if dbpedia_uri:
        for old in g.objects(person_uri, OWL.sameAs):
            g.remove((person_uri, OWL.sameAs, old))
        g.add((person_uri, OWL.sameAs, URIRef(dbpedia_uri)))

        wikidata_uri = get_wikidata_combined(dbpedia_name)
        if wikidata_uri:
            g.add((person_uri, OWL.sameAs, URIRef(wikidata_uri)))

        time.sleep(0.8)

    time.sleep(0.3)

g.serialize("out_enriched.ttl", format="turtle")

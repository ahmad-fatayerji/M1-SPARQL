from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal, XSD
from rdflib.namespace import VOID, DCTERMS

local_namespaces = set([
    "http://example.org/nobel/award/",
    "http://example.org/nobel/person/",
    "http://example.org/nobel/organization/",
    "http://example.org/nobel/place/"
])

vocabularies = set([
        "http://dbpedia.org/ontology/",
        "http://schema.org/",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "http://www.w3.org/2000/01/rdf-schema#",
        "http://www.w3.org/2002/07/owl#",
        "http://xmlns.com/foaf/0.1/",
        "http://www.w3.org/2001/XMLSchema#"
    ])

def generate_void_enriched(input_ttl, output_ttl, dataset_uri, creators):
    g = Graph()
    g.parse(input_ttl, format="turtle")
    void_graph = Graph()

    dataset = URIRef(dataset_uri)

    # main statistics
    triples_count = len(g)
    classes = set(g.objects(predicate=RDF.type))
    properties = set(g.predicates())
    subjects = set(g.subjects())

    # main dataset description
    void_graph.add((dataset, RDF.type, VOID.Dataset))
    void_graph.add((dataset, VOID.triples, Literal(triples_count, datatype=XSD.integer)))
    void_graph.add((dataset, VOID.entities, Literal(len(subjects), datatype=XSD.integer)))
    void_graph.add((dataset, VOID.classes, Literal(len(classes), datatype=XSD.integer)))
    void_graph.add((dataset, VOID.properties, Literal(len(properties), datatype=XSD.integer)))
    void_graph.add((dataset, RDFS.label, Literal(f"VoID description of Nobel Prize laureates graph", datatype=XSD.string)))
    void_graph.add((dataset, DCTERMS.created, Literal("2025-11-17", datatype=XSD.date)))
    for creator in creators:
        void_graph.add((dataset, DCTERMS.creator, Literal(creator, datatype=XSD.string)))
    void_graph.add((dataset, VOID.dataDump, URIRef(input_ttl)))
    for ns in local_namespaces:
        void_graph.add((dataset, VOID.uriSpace, Literal(ns, datatype=XSD.string)))
    for v in vocabularies:
        void_graph.add((dataset, VOID.vocabulary, URIRef(v)))

    # Linksets owl:sameAs 
    sameas_links = list(g.triples((None, OWL.sameAs, None)))
    linksets = {}
    for s, _, o in sameas_links:
        if isinstance(o, URIRef):
            domain = o.split("/")[2]
            linksets.setdefault(domain, []).append((s, o))

    for domain, links in linksets.items():
        linkset_uri = URIRef(f"{dataset_uri}/linkset/{domain}")
        void_graph.add((dataset, VOID.subset, linkset_uri))
        void_graph.add((linkset_uri, RDF.type, VOID.Linkset))
        void_graph.add((linkset_uri, VOID.linkPredicate, OWL.sameAs))
        void_graph.add((linkset_uri, VOID.triples, Literal(len(links), datatype=XSD.integer)))
        void_graph.add((linkset_uri, VOID.subjectsTarget, dataset))
        void_graph.add((linkset_uri, VOID.objectsTarget, URIRef(f"http://{domain}")))

    # export VoID graph
    void_graph.serialize(output_ttl, format="turtle")
    print(f"VoID enrichi généré dans : {output_ttl}")

if __name__ == "__main__":
    generate_void_enriched(
        input_ttl="Step4/out_enriched_complete.ttl",
        output_ttl="void.ttl",
        dataset_uri="http://example.org/nobel",
        creators=["Ahmad Fatayerji", "Hugo Piard", "Louis Boulanger", "Ziad Ijja"]
    )

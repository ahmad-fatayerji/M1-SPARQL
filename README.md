# 🌐 Projet Web Sémantique — Prix Nobel RDF

## Présentation

Ce projet transforme un fichier CSV contenant les informations des lauréats du **Prix Nobel** en un graphe **RDF** au format **Turtle**, interrogeable via **SPARQL** sur un serveur local [Apache Jena Fuseki](https://jena.apache.org/documentation/fuseki2/).

---

## Contenu du repo

- `converter.py` — Script Python pour convertir le CSV en TTL
- `nobel-prize-laureates.csv` — Données sources
- `nobel_complete.ttl` — Graphe RDF généré
- `marie_curie_example.png` — Exemple visuel de la structure RDF (Marie Curie)

---

## Prérequis et installation

Prérequis côté machine :

- Python 3.10+ (testé avec 3.12)
- pip (installé avec Python)

Installer les dépendances Python :

```powershell
pip install -r .\requirements.txt
```

Packages utilisés :

- `pandas` pour lire le CSV
- `rdflib` pour construire et sérialiser le graphe RDF

## Conversion CSV → RDF

Le script `converter.py` lit le fichier CSV et génère automatiquement un fichier `nobel_complete.ttl` :

```bash
python3 converter.py
```

Le fichier TTL peut ensuite être importé dans un serveur local comme Fuseki pour exécuter des requêtes SPARQL.

---

## Modélisation RDF

Deux vocabulaires principaux sont utilisés :

- [`schema.org`](https://schema.org/) pour les personnes, lieux, récompenses, organisations
- [`FOAF`](http://xmlns.com/foaf/spec/) pour les noms des personnes et organisations

### Types et ressources générées

| Élément      | Classe RDF            | Exemple URI                              |
| ------------ | --------------------- | ---------------------------------------- |
| Lauréat      | `foaf:Person`         | `nobel:person/Marie_Curie`               |
| Récompense   | `schema:Award`        | `nobel:award/Marie_Curie_1911_Chemistry` |
| Lieu         | `schema:Place`        | `place:Born_Paris_France`                |
| Organisation | `schema:Organization` | `organization:Sorbonne`                  |

Les propriétés couvrent la naissance (`schema:birthPlace`, `schema:birthDate`), décès, genre, affiliation, lieu d’activité, année et catégorie du prix, ainsi que la motivation.

---

## Utilisation avec Fuseki

1. Lancer le serveur local :

   ```bash
   fuseki-server
   ```

2. Créer un dataset via l’interface [http://localhost:3030](http://localhost:3030)

3. Importer `nobel_complete.ttl` et exécuter des requêtes SPARQL.

---

## 🔍 Idées de requêtes SPARQL

Quelques pistes pertinentes :

- Répartition hommes / femmes parmi les lauréats et au fil des décénies
- Évolution temporelle du nombre de prix par décennie
- Distribution des catégories (Physique, Chimie, Médecine…)
- Détection de migrations scientifiques (pays de naissance ≠ affiliation)

---

## Technologies

- **Python**, `pandas`, `rdflib`
- **RDF / Turtle**, **SPARQL**
- **Apache Jena Fuseki**
- Vocabulaires : `schema.org`, `FOAF`

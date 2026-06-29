"""SQL queries."""


# 1. Queries for all changed entities
def query_changed_entities(table_name: str) -> str:
    """SQL query for changed entities."""

    changed_entities = f"""
SELECT
    id,
    modified
FROM content.{table_name}
WHERE modified > %(modified)s
   OR (modified = %(modified)s AND id > %(id)s)
ORDER BY modified, id
LIMIT %(limit)s;
"""
    return changed_entities


# 2. Queries for film works affected by the changes.

# Query for film works by their ids.
FILM_WORK_IDS_BY_SELF = """
SELECT
    fw.id,
    fw.modified
FROM content.film_work AS fw
WHERE fw.id = ANY(%(entity_ids)s)
ORDER BY fw.modified, fw.id;
"""

# Query for film works related to changed genres.
FILM_WORK_IDS_BY_GENRE = """
SELECT DISTINCT
    fw.id,
    fw.modified
FROM content.film_work AS fw
JOIN content.genre_film_work AS gfw ON gfw.film_work_id = fw.id
WHERE gfw.genre_id = ANY(%(entity_ids)s)
ORDER BY fw.modified, fw.id;
"""

# Query for film works related to changed persons.
FILM_WORK_IDS_BY_PERSON = """
SELECT DISTINCT
    fw.id,
    fw.modified
FROM content.film_work AS fw
JOIN content.person_film_work AS pfw ON pfw.film_work_id = fw.id
WHERE pfw.person_id = ANY(%(entity_ids)s)
ORDER BY fw.modified, fw.id;
"""

# 3. Collect missing information for writing to Elasticsearch.

# Return film_work fields.
FILM_WORK_DETAILS = """
SELECT
    fw.id,
    fw.rating AS imdb_rating,
    fw.title,
    fw.description,
    fw.subscription_level,
    fw.modified
FROM content.film_work AS fw
WHERE fw.id = ANY(%(film_work_ids)s)
ORDER BY fw.modified, fw.id;
"""

# Return genres by the list of film_work_ids
FILM_WORK_GENRES = """
SELECT
    gfw.film_work_id,
    g.id,
    g.name
FROM content.genre_film_work AS gfw
JOIN content.genre AS g ON g.id = gfw.genre_id
WHERE gfw.film_work_id = ANY(%(film_work_ids)s)
ORDER BY gfw.film_work_id, g.name;
"""

# Return persons and their roles by the list of film_work_ids
FILM_WORK_PERSONS = """
SELECT
    pfw.film_work_id,
    pfw.role,
    p.id,
    p.full_name
FROM content.person_film_work AS pfw
JOIN content.person AS p ON p.id = pfw.person_id
WHERE pfw.film_work_id = ANY(%(film_work_ids)s)
ORDER BY pfw.film_work_id, pfw.role, p.full_name;
"""

GENRE_DETAILS = """
SELECT
    id,
    name
FROM content.genre
WHERE id = ANY(%(genre_ids)s)
ORDER BY id;
"""

# Return person details and their films with roles for person index
PERSON_DETAILS = """
SELECT
    p.id as person_id,
    p.full_name,
    pfw.film_work_id as fw_id,
    pfw.role
FROM content.person p
LEFT JOIN content.person_film_work pfw ON pfw.person_id = p.id
WHERE p.id = ANY(%(person_ids)s);
"""

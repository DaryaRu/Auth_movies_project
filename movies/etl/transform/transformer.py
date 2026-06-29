"""Transforms PostgreSQL into ETL models."""

from uuid import UUID

from models import FilmPerson, FilmWork, Genre, Person


def build_film_work(
    row: dict,
    genres: list[Genre],
    persons: dict[str, list[Person]],
) -> FilmWork:
    """Build a FilmWork document."""
    directors = list(persons["directors"])
    actors = list(persons["actors"])
    writers = list(persons["writers"])
    result = FilmWork(
        id=row["id"],
        imdb_rating=row.get("imdb_rating"),
        genres=genres,
        title=row["title"],
        description=row.get("description"),
        subscription_level=row.get("subscription_level", 0),
        directors_names=[person.name for person in directors],
        actors_names=[person.name for person in actors],
        writers_names=[person.name for person in writers],
        directors=directors,
        actors=actors,
        writers=writers,
    )
    return result


def build_genre(row: dict) -> Genre:
    return Genre(**row)


def build_person(row: dict) -> Person:
    """Build a single Person document for Pydantic."""
    return Person(**row)


def build_persons_from_rows(rows: list[dict]) -> list[Person]:
    """Group flat SQL rows by person_id and transform to Pydantic models."""
    persons_data = {}

    for row in rows:
        p_id = row["person_id"]

        if p_id not in persons_data:
            persons_data[p_id] = {
                "id": p_id if isinstance(p_id, UUID) else UUID(p_id),
                "name": row["full_name"],
                "films": [],
            }

        if row["fw_id"]:
            role = row["role"]
            film_id = (
                row["fw_id"]
                if isinstance(row["fw_id"], UUID)
                else UUID(row["fw_id"])
            )

            existing_film = next(
                (f for f in persons_data[p_id]["films"] if f["id"] == film_id),
                None,
            )

            if existing_film:
                if role and role not in existing_film["roles"]:
                    existing_film["roles"].append(role)
            else:
                persons_data[p_id]["films"].append(
                    {"id": film_id, "roles": [role] if role else []}
                )

    return [build_person(data) for data in persons_data.values()]


def group_genres_by_film(rows: list[dict]) -> dict:
    """Group genres by film_work_id."""
    grouped_genres: dict = {}
    for row in rows:
        film_work_id = row["film_work_id"]
        grouped_genres.setdefault(film_work_id, [])
        genre = Genre(id=row["id"], name=row["name"])
        if genre.id not in {g.id for g in grouped_genres[film_work_id]}:
            grouped_genres[film_work_id].append(genre)
    return grouped_genres


def group_persons_by_film(rows: list[dict]) -> dict:
    """Group persons by film_work_id and group them by roles."""
    grouped_persons: dict = {}
    for row in rows:
        film_work_id = row["film_work_id"]
        film_persons = grouped_persons.setdefault(
            film_work_id,
            {
                "directors": [],
                "actors": [],
                "writers": [],
            },
        )
        role = row["role"]

        person_id = (
            row["id"] if isinstance(row["id"], UUID) else UUID(row["id"])
        )
        person = FilmPerson(id=person_id, name=row["full_name"])

        if role == "director":
            target_key = "directors"
        elif role == "actor":
            target_key = "actors"
        else:
            target_key = "writers"
        if person.id not in {p.id for p in film_persons[target_key]}:
            film_persons[target_key].append(person)
    return grouped_persons

"""Test film data for ES."""

TEST_GENRE_ID = "3d8d3b6e-13c5-436f-89d7-ec4b055536d4"
TEST_PERSON_ID = "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95"
FILMS_IDS = [
    "2d5a8f1c-7e4b-4d3a-b9c6-8a1f5d2e7c64",
    "b1f7c5a2-4d8e-4a3d-b6c9-2e1a7d5f8c11",
    "e5a2d8f1-7c4b-4f3d-b9a6-1d5e8c2a7f52",
    "73c1a5d8-4e7f-4a2d-b6c9-5f1a8d2e7c85",
    "c1d8a5f2-7e4b-4d3a-b9c6-2f5a1e7d8c19",
    "18a5f2d7-4c8e-4a3d-b6f9-7d1c5a2e8f43",
    "d7c2a5f1-8e4b-4d3a-b9c6-1f5e8a2d7c70",
    "5f1a8d2c-7e4b-4a3d-b6c9-2d7a5e1f8c94",
    "a8d5c1f2-4e7b-4f3d-b9a6-7c2e1d5a8f26",
    "2c7a5d1f-8e4b-4a3d-b6c9-5f1e8d2a7c61",
]
FILM_DATA_LIST_LENGTH = len(FILMS_IDS)

FILMS_DATA = [
    {
        "id": FILMS_IDS[i],
        "title": f"The Star Part {i}",
        "imdb_rating": float(1.0 + (i / 10)),
        "description": f"Description number {i}",
        "directors": [],
        "actors": [{"id": TEST_PERSON_ID, "name": "Ann"}],
        "writers": [],
        "genres": [{"id": TEST_GENRE_ID, "name": "Action"}],
    }
    for i in range(FILM_DATA_LIST_LENGTH)
]

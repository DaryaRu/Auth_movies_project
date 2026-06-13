from http import HTTPStatus

NOT_EXISTING_UUID = "00000000-0000-0000-0000-000000000000"

ACCESS_DENIED_CASES = [
    ("no_auth", HTTPStatus.UNAUTHORIZED),
    ("regular_user", HTTPStatus.FORBIDDEN),
]

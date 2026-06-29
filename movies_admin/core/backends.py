from functools import lru_cache
import http
import logging
from typing import Any
import uuid

import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from jose import JWTError, jwt

User = get_user_model()
    

class CustomBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        url = settings.AUTH_API_LOGIN_URL
        request_id = request.headers.get("X-Request-Id")
        payload = {'email': username, 'password': password}
        try:
            response = requests.post(url, json=payload, timeout=5, headers={"X-Request-Id": request_id})
        except requests.RequestException:
            logging.error("Auth API unavailable")
            return None
        if response.status_code != http.HTTPStatus.OK:
            logging.error(f"Login status code - {response.status_code}")
            logging.error(f"Login error - {response.text}")
            return None
        
        access_token = response.json()["access_token"]

        public_key = self._get_public_key()
        if public_key is None:
            return None

        try:
            payload = self._get_token_payload(access_token, public_key)
        except (JWTError, AttributeError) as exc:
            logging.error(f"Decode token error: {exc}")
            self._get_public_key.cache_clear()
            public_key = self._get_public_key()
            if public_key is None:
                return None
            try:
                payload = self._get_token_payload(access_token, public_key)
            except Exception as exc:
                logging.error(f"Second decode token failed: {exc}")
                return None

        if not payload.get("is_superuser"):
            return None

        user_id = payload["sub"]

        user, _ = User.objects.update_or_create(
            id=user_id,
            defaults={
                "email": username,
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
            },
        )

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_public_key() -> str | None:
        response = requests.get(
            settings.AUTH_API_PUBLIC_KEY_URL,
            timeout=5,
            headers={"X-Request-Id": str(uuid.uuid4())},
        )
        if response.status_code != http.HTTPStatus.OK:
            logging.error(f"Public key status code - {response.status_code}")
            logging.error(f"Public key error - {response.text}")
            return None

        return response.text
    
    @staticmethod
    def _get_token_payload(access_token: str, public_key: str) -> dict[str, Any]:
        return jwt.decode(
            access_token,
            public_key,
            algorithms=settings.JWT_ALGORITHM,
        )

import http
import logging

import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from jose import JWTError, jwt

User = get_user_model()
    

class CustomBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        url = settings.AUTH_API_LOGIN_URL
        headers = {"X-Request-Id": request.headers.get("X-Request-Id")}
        payload = {'email': username, 'password': password}
        response = requests.post(url, json=payload, timeout=5, headers=headers)
        if response.status_code != http.HTTPStatus.OK:
            logging.error(f"Login status code - {response.status_code}")
            logging.error(f"Login error - {response.json()}")
            return None
        
        access_token = response.json()["access_token"]

        public_key_response = requests.get(
            settings.AUTH_API_PUBLIC_KEY_URL,
            timeout=5,
            headers=headers,
        )
        if public_key_response.status_code != http.HTTPStatus.OK:
            logging.error(f"Public key status code - {response.status_code}")
            logging.error(f"Public key error - {response.json()}")
            return None

        public_key = public_key_response.text

        try:
            payload = jwt.decode(
                access_token,
                public_key,
                algorithms=settings.JWT_ALGORITHM,
            )
        except (JWTError, AttributeError) as exc:
            logging.error(f"Decode token error: {exc}")
            return None

        if not payload.get("is_superuser"):
            return None

        user_id = payload["sub"]

        user, _ = User.objects.get_or_create(
            id=user_id,
            defaults={
                "email": username,
            },
        )

        user.email = username
        user.is_superuser = True
        user.is_active = True
        user.is_staff = True
        user.save(
            update_fields=[
                "email",
                "is_superuser",
                "is_staff",
                "is_active",
            ]
        )

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

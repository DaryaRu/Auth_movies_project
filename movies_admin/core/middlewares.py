from django.conf import settings
from django.http import JsonResponse
from opentelemetry import trace


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-Id")

        if (
            not request_id
            and request.path not in settings.EXCLUDED_PATHS
        ):
            return JsonResponse(
                {
                    "detail": {
                        "error": "X-Request-Id is required",
                    }
                },
                status=400,
            )

        span = trace.get_current_span()

        if request_id and span.is_recording():
            span.set_attribute("request.id", request_id)

        response = self.get_response(request)

        if request_id:
            response["X-Request-Id"] = request_id

        return response

"""Настройка OpenTelemetry трассировки."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

from src.core.config import settings


def configure_tracer() -> None:
    """Настраивает провайдер трассировки и экспортеры."""
    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME,
        "deployment.environment": settings.ENVIRONMENT,
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True,
            )
        )
    )
    if settings.DEBUG:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
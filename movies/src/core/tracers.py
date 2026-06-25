from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider        
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)

from core import config


def configure_tracer() -> None:
    resource = Resource.create({
        "service.name": config.OTEL_SERVICE_NAME,
        "deployment.environment": config.ENVIRONMENT,
    })
    provider = TracerProvider(resource=resource)

    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True,
            )
        )
    )

    if config.DEBUG:
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(provider)

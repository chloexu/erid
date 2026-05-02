from observability.tracer import NullTracer

_tracer: NullTracer = NullTracer()


def get_tracer() -> NullTracer:
    return _tracer


def set_tracer(t: NullTracer) -> None:
    global _tracer
    _tracer = t

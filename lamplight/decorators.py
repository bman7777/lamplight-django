"""Project-wide view decorators."""

from functools import wraps

from django.http import JsonResponse
from pydantic import ValidationError


def validate_params(schema_cls, path_fields=()):
    """Validate URL + query params against a pydantic schema before calling the view.

    Path fields are pulled from the view's URL kwargs; the remaining schema
    fields are read from request.GET. On success, the decorated view is called
    as `view(request, params, ...)` where `params` is the validated schema
    instance. On failure a 400 JsonResponse is returned with the first error.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            payload = {
                field: kwargs.pop(field) for field in path_fields if field in kwargs
            }
            for field in schema_cls.model_fields:
                if field in payload:
                    continue
                if field in request.GET:
                    payload[field] = request.GET[field]
            try:
                params = schema_cls.model_validate(payload)
            except ValidationError as exc:
                first = exc.errors()[0]
                field = first["loc"][0] if first["loc"] else "input"
                return JsonResponse({"error": f"{field}: {first['msg']}"}, status=400)
            return view(request, params, *args, **kwargs)

        return wrapper

    return decorator

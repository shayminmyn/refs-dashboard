"""
Middleware chuyển đổi JSON response keys snake_case → camelCase.
Frontend gửi request body bằng snake_case, middleware chỉ cần xử lý response.
"""

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _snake_to_camel(s: str) -> str:
    if "_" not in s or s.startswith("_"):
        return s
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _convert_keys(obj):
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _convert_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_keys(i) for i in obj]
    return obj


class CamelCaseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(body)
            data = _convert_keys(data)
            new_body = json.dumps(data, default=str).encode()
        except Exception:
            new_body = body

        headers = dict(response.headers)
        headers["content-length"] = str(len(new_body))

        return Response(
            content=new_body,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )

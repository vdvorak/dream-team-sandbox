from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Domain error with a stable code. Response shape: {code, details}.

    Never str(exc)/stack trace in the response (see constitution + rules/error-responses).
    """

    def __init__(self, code: str, status: int = 400, details: dict | None = None):
        self.code = code
        self.status = status
        self.details = details


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    body: dict = {"code": exc.code}
    if exc.details:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status, content=body)

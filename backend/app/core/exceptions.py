from typing import Any


class AppError(Exception):
    """Domain error carrying a stable code and HTTP status."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


class NotFoundError(AppError):
    def __init__(self, message: str = "Data tidak ditemukan.") -> None:
        super().__init__("NOT_FOUND", message, 404)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(code, message, 409)


class BusinessRuleError(AppError):
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION") -> None:
        super().__init__(code, message, 422)


class AuthError(AppError):
    def __init__(
        self, message: str = "Kredensial tidak valid.", code: str = "UNAUTHENTICATED"
    ) -> None:
        super().__init__(code, message, 401)


class PermissionError_(AppError):
    def __init__(self, message: str = "Anda tidak memiliki izin untuk tindakan ini.") -> None:
        super().__init__("FORBIDDEN", message, 403)

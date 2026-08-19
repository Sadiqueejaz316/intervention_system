class AppError(Exception):
    """Base class for errors that map onto an HTTP response."""

    status_code: int = 400

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404


class DomainValidationError(AppError):
    status_code = 422


class InvalidTransitionError(AppError):
    status_code = 409


class ConflictError(AppError):
    status_code = 409


class PermissionDeniedError(AppError):
    status_code = 403

class AppError(Exception):
    def __init__(self, status_code: int, message: str, error_code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.error_code = error_code


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在", error_code: str = "NOT_FOUND") -> None:
        super().__init__(404, message, error_code)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权访问该资源", error_code: str = "FORBIDDEN") -> None:
        super().__init__(403, message, error_code)


class ConflictError(AppError):
    def __init__(self, message: str, error_code: str = "CONFLICT") -> None:
        super().__init__(409, message, error_code)


class ValidationError(AppError):
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR") -> None:
        super().__init__(400, message, error_code)

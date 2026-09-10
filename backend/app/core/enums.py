from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class GenerationType(StrEnum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class PublishStatus(StrEnum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"

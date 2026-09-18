from typing import Literal, cast

from app.core.config import get_settings

SupportedLocale = Literal["zh-CN", "ja-JP", "en-US"]
SUPPORTED_LOCALES: tuple[SupportedLocale, ...] = ("zh-CN", "ja-JP", "en-US")


def normalize_locale(value: str | None) -> SupportedLocale | None:
    if not value:
        return None
    normalized = value.strip().replace("_", "-").lower()
    if normalized.startswith("zh"):
        return "zh-CN"
    if normalized.startswith("ja"):
        return "ja-JP"
    if normalized.startswith("en"):
        return "en-US"
    return None


def locale_from_accept_language(value: str | None) -> SupportedLocale | None:
    candidates: list[tuple[float, int, SupportedLocale]] = []
    for index, item in enumerate((value or "").split(",")):
        parts = [part.strip() for part in item.split(";")]
        locale = normalize_locale(parts[0])
        if locale is None:
            continue
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.lower().startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        if quality > 0:
            candidates.append((quality, -index, locale))
    return max(candidates, default=(0.0, 0, None))[2]


def resolve_locale(
    *, preferred_locale: str | None = None, accept_language: str | None = None
) -> SupportedLocale:
    return (
        normalize_locale(preferred_locale)
        or locale_from_accept_language(accept_language)
        or normalize_locale(get_settings().default_locale)
        or "zh-CN"
    )


_ZH_MESSAGES: dict[str, str] = {
    "INVALID_CREDENTIALS": "用户名或密码错误",
    "ACCOUNT_DISABLED": "账号不存在或已停用",
    "NOT_AUTHENTICATED": "请先登录",
    "INVALID_TOKEN": "登录凭证无效或已过期",
    "ADMIN_REQUIRED": "仅管理员可以访问此功能",
    "FORBIDDEN": "无权访问该资源",
    "REQUEST_VALIDATION_ERROR": "请求参数格式错误",
    "INTERNAL_ERROR": "服务内部错误",
    "USER_EXISTS": "用户名或邮箱已存在",
    "USER_NOT_FOUND": "用户不存在",
    "CANNOT_DELETE_SELF": "不能删除当前登录账号",
    "USER_HAS_RESOURCES": "用户已有业务数据，请改为停用账号",
    "MODEL_NOT_FOUND": "视频模型不存在",
    "MODEL_DISABLED": "所选视频模型已停用",
    "MODEL_ACCOUNT_DISABLED": "所选模型账号已停用",
    "MODEL_PROVIDER_DISABLED": "所选模型服务商已停用",
    "TEXT_TO_VIDEO_UNSUPPORTED": "所选模型不支持文生视频",
    "IMAGE_TO_VIDEO_UNSUPPORTED": "所选模型不支持图生视频",
    "INVALID_DURATIONS": "视频时长不在当前模型允许范围内",
    "INVALID_ASPECT_RATIOS": "画面比例不在当前生成类型允许范围内",
    "INVALID_RESOLUTIONS": "分辨率不在当前模型允许范围内",
    "PROMPT_REQUIRED": "视频描述不能为空",
    "PROMPT_TOO_LONG": "视频描述超过当前模型长度限制",
    "INVALID_IMAGE_TYPE": "参考图片仅支持 JPG、PNG 或 WebP",
    "INVALID_IMAGE_CONTENT": "参考图片内容无效",
    "PLATFORM_DISABLED": "所选发布平台已停用",
    "ACCOUNT_PLATFORM_MISMATCH": "发布账号不属于所选平台",
    "PLATFORM_VIDEO_UNSUPPORTED": "所选平台不支持视频发布",
    "PLATFORM_COVER_UNSUPPORTED": "所选平台不支持自定义封面",
    "PLATFORM_FIELD_REQUIRED": "平台必填字段缺失",
    "PLATFORM_FIELD_TOO_LONG": "平台字段超过长度限制",
    "QUEUE_UNAVAILABLE": "任务队列暂时不可用",
    "VIDEO_NOT_FOUND": "视频不存在或已删除",
    "PUBLISH_TASK_NOT_FOUND": "发布任务不存在",
    "PUBLISHED_POST_NOT_FOUND": "发布结果不存在",
}

_EN_MESSAGES: dict[str, str] = {
    "INVALID_CREDENTIALS": "Incorrect username or password",
    "ACCOUNT_DISABLED": "The account does not exist or is disabled",
    "NOT_AUTHENTICATED": "Please sign in",
    "INVALID_TOKEN": "The login credential is invalid or expired",
    "ADMIN_REQUIRED": "Only administrators can access this feature",
    "FORBIDDEN": "You are not allowed to access this resource",
    "REQUEST_VALIDATION_ERROR": "The request parameters are invalid",
    "INTERNAL_ERROR": "Internal server error",
    "USER_EXISTS": "The username or email already exists",
    "USER_NOT_FOUND": "User not found",
    "CANNOT_DELETE_SELF": "You cannot delete the currently signed-in account",
    "USER_HAS_RESOURCES": "The user has business data; disable the account instead",
    "MODEL_NOT_FOUND": "Video model not found",
    "MODEL_DISABLED": "The selected video model is disabled",
    "MODEL_ACCOUNT_DISABLED": "The selected model account is disabled",
    "MODEL_PROVIDER_DISABLED": "The selected model provider is disabled",
    "TEXT_TO_VIDEO_UNSUPPORTED": "The selected model does not support text-to-video generation",
    "IMAGE_TO_VIDEO_UNSUPPORTED": "The selected model does not support image-to-video generation",
    "INVALID_DURATIONS": "The duration is outside the range supported by this model",
    "INVALID_ASPECT_RATIOS": "The aspect ratio is not supported for this generation type",
    "INVALID_RESOLUTIONS": "The resolution is not supported by this model",
    "PROMPT_REQUIRED": "The video description is required",
    "PROMPT_TOO_LONG": "The video description exceeds the model limit",
    "INVALID_IMAGE_TYPE": "Reference images must be JPG, PNG, or WebP",
    "INVALID_IMAGE_CONTENT": "The reference image is invalid",
    "PLATFORM_DISABLED": "The selected publish platform is disabled",
    "ACCOUNT_PLATFORM_MISMATCH": "The publish account does not belong to the selected platform",
    "PLATFORM_VIDEO_UNSUPPORTED": "The selected platform does not support video publishing",
    "PLATFORM_COVER_UNSUPPORTED": "The selected platform does not support a custom cover",
    "PLATFORM_FIELD_REQUIRED": "A required platform field is missing",
    "PLATFORM_FIELD_TOO_LONG": "A platform field exceeds its length limit",
    "QUEUE_UNAVAILABLE": "The task queue is temporarily unavailable",
    "VIDEO_NOT_FOUND": "The video does not exist or was deleted",
    "PUBLISH_TASK_NOT_FOUND": "Publish task not found",
    "PUBLISHED_POST_NOT_FOUND": "Publish result not found",
}

_JA_MESSAGES: dict[str, str] = {
    "INVALID_CREDENTIALS": "ユーザー名またはパスワードが正しくありません",
    "ACCOUNT_DISABLED": "アカウントが存在しないか無効です",
    "NOT_AUTHENTICATED": "ログインしてください",
    "INVALID_TOKEN": "ログイン認証が無効または期限切れです",
    "ADMIN_REQUIRED": "この機能は管理者のみ利用できます",
    "FORBIDDEN": "このリソースへのアクセス権限がありません",
    "REQUEST_VALIDATION_ERROR": "リクエストパラメータが正しくありません",
    "INTERNAL_ERROR": "サーバー内部エラー",
    "USER_EXISTS": "ユーザー名またはメールは既に存在します",
    "USER_NOT_FOUND": "ユーザーが見つかりません",
    "CANNOT_DELETE_SELF": "現在ログイン中のアカウントは削除できません",
    "USER_HAS_RESOURCES": "ユーザーに業務データがあるため、アカウントを無効にしてください",
    "MODEL_NOT_FOUND": "動画モデルが見つかりません",
    "MODEL_DISABLED": "選択した動画モデルは無効です",
    "MODEL_ACCOUNT_DISABLED": "選択したモデルアカウントは無効です",
    "MODEL_PROVIDER_DISABLED": "選択したモデルプロバイダーは無効です",
    "TEXT_TO_VIDEO_UNSUPPORTED": "選択したモデルはテキストから動画に対応していません",
    "IMAGE_TO_VIDEO_UNSUPPORTED": "選択したモデルは画像から動画に対応していません",
    "INVALID_DURATIONS": "動画の長さは現在のモデルの許容範囲外です",
    "INVALID_ASPECT_RATIOS": "アスペクト比は現在の生成方式で利用できません",
    "INVALID_RESOLUTIONS": "解像度は現在のモデルで利用できません",
    "PROMPT_REQUIRED": "動画の説明を入力してください",
    "PROMPT_TOO_LONG": "動画の説明がモデルの上限を超えています",
    "INVALID_IMAGE_TYPE": "参照画像は JPG、PNG、WebP のみ対応しています",
    "INVALID_IMAGE_CONTENT": "参照画像が無効です",
    "PLATFORM_DISABLED": "選択した公開プラットフォームは無効です",
    "ACCOUNT_PLATFORM_MISMATCH": "公開アカウントが選択したプラットフォームに属していません",
    "PLATFORM_VIDEO_UNSUPPORTED": "選択したプラットフォームは動画公開に対応していません",
    "PLATFORM_COVER_UNSUPPORTED": "選択したプラットフォームはカスタムカバーに対応していません",
    "PLATFORM_FIELD_REQUIRED": "プラットフォームの必須フィールドがありません",
    "PLATFORM_FIELD_TOO_LONG": "プラットフォームのフィールドが長すぎます",
    "QUEUE_UNAVAILABLE": "タスクキューを一時的に利用できません",
    "VIDEO_NOT_FOUND": "動画が存在しないか削除されています",
    "PUBLISH_TASK_NOT_FOUND": "公開タスクが見つかりません",
    "PUBLISHED_POST_NOT_FOUND": "公開結果が見つかりません",
}

_MESSAGES: dict[SupportedLocale, dict[str, str]] = {
    "zh-CN": _ZH_MESSAGES,
    "ja-JP": _JA_MESSAGES,
    "en-US": _EN_MESSAGES,
}
_GENERIC: dict[SupportedLocale, str] = {
    "zh-CN": "请求处理失败",
    "ja-JP": "リクエストの処理に失敗しました",
    "en-US": "The request could not be processed",
}


def translate_error(error_code: str, fallback: str, locale: str | None) -> str:
    selected = normalize_locale(locale) or cast(SupportedLocale, "zh-CN")
    translated = _MESSAGES[selected].get(error_code)
    if translated:
        return translated
    return fallback if selected == "zh-CN" else _GENERIC[selected]

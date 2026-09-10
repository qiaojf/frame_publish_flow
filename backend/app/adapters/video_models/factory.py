from collections.abc import Callable

from app.adapters.video_models.base import VideoModelAdapter
from app.adapters.video_models.mock import MockVideoModelAdapter
from app.models import VideoModel


class ModelAdapterFactory:
    _registry: dict[str, Callable[[VideoModel], VideoModelAdapter]] = {
        "mock_video": lambda model: MockVideoModelAdapter(model.extra_config),
    }

    @classmethod
    def register(cls, adapter_type: str, builder: Callable[[VideoModel], VideoModelAdapter]) -> None:
        cls._registry[adapter_type] = builder

    @classmethod
    def create(cls, model: VideoModel) -> VideoModelAdapter:
        builder = cls._registry.get(model.adapter_type)
        if builder is None:
            raise RuntimeError(f"视频模型适配器“{model.adapter_type}”尚未实现或注册")
        return builder(model)

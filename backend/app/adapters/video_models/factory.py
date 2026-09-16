from collections.abc import Callable

from app.adapters.video_models.base import VideoModelAdapter
from app.adapters.video_models.google_veo31 import GoogleVeo31Adapter
from app.adapters.video_models.luma_ray32 import LumaRay32Adapter
from app.adapters.video_models.minimax_hailuo23 import MiniMaxHailuo23Adapter
from app.adapters.video_models.mock import MockVideoModelAdapter
from app.adapters.video_models.runway_gen45 import RunwayGen45Adapter
from app.adapters.video_models.runway_seedance25 import RunwaySeedance25Adapter
from app.models import VideoModel


class ModelAdapterFactory:
    _registry: dict[str, Callable[[VideoModel], VideoModelAdapter]] = {
        "mock_video": lambda model: MockVideoModelAdapter(model.extra_config),
        "google_veo31": GoogleVeo31Adapter,
        "runway_gen45": RunwayGen45Adapter,
        "runway_seedance25": RunwaySeedance25Adapter,
        "luma_ray32": LumaRay32Adapter,
        "minimax_hailuo23": MiniMaxHailuo23Adapter,
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

from abc import ABC, abstractmethod
from typing import Any


class JudgeProvider(ABC):
    name = "base"

    @abstractmethod
    async def judge(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

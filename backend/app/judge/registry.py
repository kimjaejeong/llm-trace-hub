from app.judge.providers.heuristic import HeuristicJudgeProvider
from app.judge.providers.llm import LLMJudgeProvider


class JudgeRegistry:
    def __init__(self, llm_endpoint: str | None = None):
        self.heuristic = HeuristicJudgeProvider()
        self.llm = LLMJudgeProvider(endpoint=llm_endpoint)

    def get(self, name: str):
        if name == "heuristic":
            return self.heuristic
        if name == "llm":
            return self.llm
        raise KeyError(f"Unknown judge provider: {name}")

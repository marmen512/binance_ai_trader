from dataclasses import dataclass
from typing import List, Dict


@dataclass
class LeaderScore:
    leader_id: str
    score: float
    max_allocation: float = 0.5


class PortfolioRouter:
    """
    Distributes capital across multiple leaders based on score.
    """

    def __init__(self, total_capital: float):
        self.total_capital = total_capital

    def allocate(self, leaders: List[LeaderScore]) -> Dict[str, float]:
        if not leaders:
            return {}

        total_score = sum(max(l.score, 0) for l in leaders)

        if total_score == 0:
            return {l.leader_id: 0 for l in leaders}

        allocations = {}

        for l in leaders:
            raw = (l.score / total_score) * self.total_capital
            capped = min(raw, l.max_allocation * self.total_capital)
            allocations[l.leader_id] = round(capped, 2)

        return allocations

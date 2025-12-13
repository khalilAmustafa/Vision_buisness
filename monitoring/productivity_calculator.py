

# monitoring/productivity_calculator.py

from __future__ import annotations

from monitoring.base_productivity_calculator import BaseProductivityCalculator


class ProductivityCalculator(BaseProductivityCalculator):
    """
    Combines:
      - focused_seconds      (from camera)
      - non_work_seconds     (from PC monitor)
      - idle_seconds         (from PC monitor)
      - late_minutes         (from shift tracker)
    into a 0–100 productivity score.
    """

    def calculate_score(
        self,
        focused_seconds: float,
        non_work_seconds: float,
        idle_seconds: float,
        late_minutes: int,
    ) -> float:
        total = focused_seconds + non_work_seconds + idle_seconds
        if total <= 0:
            return 0.0

        focus_ratio = focused_seconds / total
        non_work_ratio = non_work_seconds / total
        idle_ratio = idle_seconds / total

        # Base score: how much of the time was focused
        base_score = focus_ratio * 100.0

        # Penalties
        non_work_penalty = non_work_ratio * 40.0   # strong penalty
        idle_penalty = idle_ratio * 20.0           # medium penalty
        late_penalty = min(max(late_minutes, 0) * 0.5, 20.0)  # up to -20

        score = base_score - non_work_penalty - idle_penalty - late_penalty
        score = max(0.0, min(100.0, score))
        return score

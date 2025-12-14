# monitoring/base_productivity_calculator.py

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class ProductivityCategory(str, Enum):
    PERFECT = "Perfect"
    VERY_GOOD = "Very Good"
    GOOD = "Good"
    BAD = "Bad"
    WORSE = "Worse"


class BaseProductivityCalculator(ABC):
    """
    Base class for productivity calculation.
    """

    @abstractmethod
    def calculate_score(
        self,
        focused_seconds: float,
        non_work_seconds: float,
        idle_seconds: float,
        late_minutes: int,
    ) -> float:
        """
        Must return a value between 0 and 100.
        """
        raise NotImplementedError

    def categorize(self, score: float) -> ProductivityCategory:
        """
        Convert numeric score into category (from the documentation).
        """
        if score >= 90:
            return ProductivityCategory.PERFECT
        if score >= 80:
            return ProductivityCategory.VERY_GOOD
        if score >= 70:
            return ProductivityCategory.GOOD
        if score >= 60:
            return ProductivityCategory.BAD
        return ProductivityCategory.WORSE

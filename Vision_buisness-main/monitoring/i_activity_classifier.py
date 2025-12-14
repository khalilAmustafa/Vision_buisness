# monitoring/i_activity_classifier.py

from abc import ABC, abstractmethod
from enum import Enum


class ActivityLabel(str, Enum):
    WORK = "WORK"
    NON_WORK = "NON_WORK"
    IDLE = "IDLE"


class IActivityClassifier(ABC):
    """
    Interface for PC activity classifiers.
    It maps the current active app / website to a label.
    """

    @abstractmethod
    def classify_activity(self, app_name: str | None) -> ActivityLabel:
        """
        Given an app_name or window title, return WORK / NON_WORK / IDLE.
        app_name can be None when system is idle.
        """
        raise NotImplementedError

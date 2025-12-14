# monitoring/i_focus_detector.py

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class FocusState(str, Enum):
    FOCUSED = "FOCUSED"
    DISTRACTED = "DISTRACTED"
    AWAY = "AWAY"


class IFocusDetector(ABC):
    """
    Interface for anything that can detect the focus state of the employee
    using a camera frame.
    """

    @abstractmethod
    def detect_focus_state(self, frame: Any) -> FocusState:
        """
        Takes a single video frame (OpenCV image) and returns
        the detected focus state.
        """
        raise NotImplementedError


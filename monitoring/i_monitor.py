
from abc import ABC, abstractmethod


class IMonitor(ABC):
    """
    Base interface for any monitoring component in Vision.
    Examples:
      - ShiftTracker
      - CameraMonitor
      - PCActivityMonitor
    """

    @abstractmethod
    def start(self) -> None:
        """Start monitoring (open camera, start timers/loops, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop monitoring and release all resources."""
        raise NotImplementedError

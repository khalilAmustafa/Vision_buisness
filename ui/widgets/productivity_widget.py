

# ui/widgets/productivity_widget.py

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

from monitoring.base_productivity_calculator import ProductivityCategory


class ProductivityWidget(QWidget):
    """
    Small widget that shows:
      - Productivity %
      - Category (Perfect / Very Good / ...)
      - Focused / Non-work / Idle minutes
      - Late minutes

    The dashboard calls `update_metrics(...)` on every refresh.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label_title = QLabel("Productivity")
        self.label_score = QLabel("Score: 0.0% (Worse)")
        self.label_focused = QLabel("Focused minutes: 0")
        self.label_non_work = QLabel("Non-work minutes: 0")
        self.label_idle = QLabel("Idle minutes: 0")
        self.label_late = QLabel("Late minutes: 0")

        layout = QVBoxLayout()
        layout.addWidget(self.label_title)
        layout.addWidget(self.label_score)
        layout.addWidget(self.label_focused)
        layout.addWidget(self.label_non_work)
        layout.addWidget(self.label_idle)
        layout.addWidget(self.label_late)

        self.setLayout(layout)

    def update_metrics(
        self,
        score: float,
        category: ProductivityCategory,
        focused_seconds: float,
        non_work_seconds: float,
        idle_seconds: float,
        late_minutes: int,
    ) -> None:
        focused_min = int(focused_seconds // 60)
        non_work_min = int(non_work_seconds // 60)
        idle_min = int(idle_seconds // 60)

        self.label_score.setText(f"Score: {score:.1f}% ({category.value})")
        self.label_focused.setText(f"Focused minutes: {focused_min}")
        self.label_non_work.setText(f"Non-work minutes: {non_work_min}")
        self.label_idle.setText(f"Idle minutes: {idle_min}")
        self.label_late.setText(f"Late minutes: {late_minutes}")

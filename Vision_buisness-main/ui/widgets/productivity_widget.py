

# ui/widgets/productivity_widget.py

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout

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
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        title = QLabel("Productivity summary")
        title.setObjectName("MutedLabel")
        self.label_score = QLabel("Score: 0.0% (Worse)")
        self.label_score.setObjectName("MetricValue")

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        self.label_focused = QLabel("Focused minutes: 0")
        self.label_non_work = QLabel("Non-work minutes: 0")
        self.label_idle = QLabel("Idle minutes: 0")
        self.label_late = QLabel("Late minutes: 0")

        metrics_grid.addWidget(self.label_focused, 0, 0)
        metrics_grid.addWidget(self.label_non_work, 0, 1)
        metrics_grid.addWidget(self.label_idle, 1, 0)
        metrics_grid.addWidget(self.label_late, 1, 1)

        layout.addWidget(title)
        layout.addWidget(self.label_score)
        layout.addLayout(metrics_grid)

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

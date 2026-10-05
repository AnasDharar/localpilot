"""Reusable widgets for LocalPilot's redesigned interface."""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui import theme

# ─── Status dot ──────────────────────────────────────────────────────────────

class StatusDot(QWidget):
    """A tiny animated circle that reflects the assistant state."""

    _COLORS = {
        "ready": theme.SUCCESS,
        "listening": theme.LISTENING,
        "processing": theme.WARNING,
        "error": theme.ERROR,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor(theme.SUCCESS)
        self._opacity = 1.0
        self._state = "ready"

        self._pulse = QPropertyAnimation(self, b"opacity", self)
        self._pulse.setDuration(900)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse.setStartValue(1.0)
        self._pulse.setEndValue(0.35)
        self._pulse.setLoopCount(-1)

    # ── Qt property for animation ────────────────────────────────────────
    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    opacity = Property(float, _get_opacity, _set_opacity)

    # ── Public API ───────────────────────────────────────────────────────
    def set_state(self, state: str) -> None:
        color_hex = self._COLORS.get(state, theme.TEXT_MUTED)
        self._color = QColor(color_hex)
        self._state = state
        if state in ("listening", "processing"):
            if self._pulse.state() != QPropertyAnimation.State.Running:
                self._pulse.start()
        else:
            self._pulse.stop()
            self._opacity = 1.0
        self.update()

    # ── Painting ─────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity)
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()


# ─── Microphone button ──────────────────────────────────────────────────────

class MicButton(QWidget):
    """A circular microphone button with idle / listening / processing / error states."""

    clicked = Signal()

    _RING_COLORS = {
        "idle": theme.ACCENT,
        "listening": theme.LISTENING,
        "processing": theme.WARNING,
        "error": theme.ERROR,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = "idle"
        self._ring_progress = 0.0
        self._enabled = True

        self.setFixedSize(theme.MIC_SIZE + 16, theme.MIC_SIZE + 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._anim = QPropertyAnimation(self, b"ring_progress", self)
        self._anim.setDuration(1200)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(360.0)
        self._anim.setLoopCount(-1)

    # ── Qt property for ring animation ───────────────────────────────────
    def _get_ring(self) -> float:
        return self._ring_progress

    def _set_ring(self, value: float) -> None:
        self._ring_progress = value
        self.update()

    ring_progress = Property(float, _get_ring, _set_ring)

    # ── Public API ───────────────────────────────────────────────────────
    def set_state(self, state: str) -> None:
        self._state = state
        if state in ("listening", "processing"):
            if self._anim.state() != QPropertyAnimation.State.Running:
                self._anim.start()
        else:
            self._anim.stop()
            self._ring_progress = 0.0
        self.setEnabled(state != "processing")
        self._enabled = state != "processing"
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._enabled
            else Qt.CursorShape.ForbiddenCursor
        )
        self.update()

    # ── Events ───────────────────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Space) and self._enabled:
            self.clicked.emit()
        else:
            super().keyPressEvent(event)

    # ── Painting ─────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = theme.MIC_SIZE / 2

        # Outer ring
        ring_color = QColor(self._RING_COLORS.get(self._state, theme.ACCENT))
        if self._state in ("listening", "processing"):
            pen = QPen(ring_color, 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            arc_rect = painter.window().adjusted(
                int(cx - r - 4), int(cy - r - 4), int(-(cx - r - 4)), int(-(cy - r - 4))
            )
            start = int(self._ring_progress * 16)
            span = 120 * 16
            painter.drawArc(arc_rect, start, span)
        else:
            pen = QPen(ring_color.darker(140), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(int(cx - r - 2), int(cy - r - 2), int(2 * r + 4), int(2 * r + 4))

        # Filled circle
        bg_color = QColor(theme.BG_INPUT)
        if self._state == "listening":
            bg_color = QColor(theme.LISTENING).darker(200)
        elif self._state == "error":
            bg_color = QColor(theme.ERROR).darker(250)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Icon
        icon = theme.MIC_ICON_LISTENING if self._state == "listening" else theme.MIC_ICON_IDLE
        font = QFont(theme.FONT_FAMILY.split(",")[0].strip(), 22)
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT_PRIMARY if self._enabled else theme.TEXT_MUTED))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, icon)

        painter.end()

    def sizeHint(self) -> QSize:  # noqa: N802
        s = theme.MIC_SIZE + 16
        return QSize(s, s)


# ─── Message bubble ─────────────────────────────────────────────────────────

class MessageBubble(QFrame):
    """A single conversation message — either from the user or the assistant."""

    def __init__(
        self,
        text: str,
        role: str = "assistant",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._role = role

        if role == "user":
            self.setStyleSheet(
                f"background: {theme.BG_INPUT}; border-radius: {theme.RADIUS_MD}; "
                f"border: 1px solid {theme.BORDER}; padding: 10px 14px;"
            )
        else:
            self.setStyleSheet(
                f"background: {theme.BG_SECONDARY}; border-radius: {theme.RADIUS_MD}; "
                f"border: 1px solid {theme.BORDER}; padding: 10px 14px;"
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        role_label = QLabel("You" if role == "user" else "LocalPilot")
        role_label.setStyleSheet(
            f"font-size: {theme.FONT_SIZE_XS}; font-weight: 600; "
            f"color: {theme.ACCENT if role == 'assistant' else theme.TEXT_SECONDARY}; "
            f"background: transparent; border: none; padding: 0;"
        )
        layout.addWidget(role_label)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet(
            f"font-size: {theme.FONT_SIZE_MD}; color: {theme.TEXT_PRIMARY}; "
            f"background: transparent; border: none; padding: 0; line-height: 1.5;"
        )
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(body)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


# ─── Activity indicator ─────────────────────────────────────────────────────

class ActivityBar(QFrame):
    """A thin bar at the bottom of the conversation card showing current action."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(
            f"background: {theme.BG_SECONDARY}; border: 1px solid {theme.BORDER}; "
            f"border-radius: {theme.RADIUS_SM}; padding: 6px 12px;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._icon = QLabel("💤")
        self._icon.setStyleSheet(f"font-size: {theme.FONT_SIZE_MD}; background: transparent; border: none;")
        layout.addWidget(self._icon)

        self._label = QLabel("Idle — ready for your voice command")
        self._label.setObjectName("activityLabel")
        self._label.setStyleSheet(
            f"font-size: {theme.FONT_SIZE_SM}; color: {theme.TEXT_SECONDARY}; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(self._label, 1)

    def set_activity(self, text: str, icon: str = "⚡") -> None:
        self._icon.setText(icon)
        self._label.setText(text)

    def set_idle(self) -> None:
        self._icon.setText("💤")
        self._label.setText("Idle — ready for your voice command")

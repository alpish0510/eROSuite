import json
import os
import sys

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE_DIR)

from utils import output_renderers
from utils import theme

from PyQt6.QtCore import Qt, QProcess, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QIntValidator, QDoubleValidator, QPixmap, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QStackedWidget,
    QLineEdit, QCheckBox, QFileDialog, QTextEdit, QMessageBox,
    QTabWidget, QSplitter, QSplitterHandle,
)


# ---------------------------------------------------------------------------
# Pipeline profile loader
# ---------------------------------------------------------------------------
_CLUSTER_PROFILE_PATH = os.path.join(_BASE_DIR, "profiles", "Cluster.json")
_SNR_PROFILE_PATH     = os.path.join(_BASE_DIR, "profiles", "SNR.json")

_registry_cache: dict | None = None


def _load_profile_from_file(path: str) -> tuple[str, dict]:
    """Load a profile JSON file and resolve its steps from the registry."""
    global _registry_cache
    if _registry_cache is None:
        registry_path = os.path.join(_BASE_DIR, "steps_registry.json")
        with open(registry_path, "r", encoding="utf-8") as fh:
            _registry_cache = json.load(fh)
    registry = _registry_cache
    with open(path, "r", encoding="utf-8") as fh:
        data: dict = json.load(fh)
    steps = []
    for step_id in data["steps"]:
        if step_id not in registry:
            raise KeyError(f"Step '{step_id}' not found in steps_registry.json")
        entry = dict(registry[step_id])
        entry["id"] = step_id
        entry["script"] = os.path.join(_BASE_DIR, entry["script"])
        steps.append(entry)
    return data["name"], {"steps": steps}


# Build the built-in profiles for Cluster and SNR
PROFILES: dict = {}
_profile_load_errors: list[str] = []
for _p in (_CLUSTER_PROFILE_PATH, _SNR_PROFILE_PATH):
    try:
        _name, _profile = _load_profile_from_file(_p)
        PROFILES[_name] = _profile
    except Exception as _e:
        _profile_load_errors.append(f"  {_p}: {_e}")


# ---------------------------------------------------------------------------
# Step state enum (plain ints for simplicity)
# ---------------------------------------------------------------------------
STEP_PENDING  = 0
STEP_ACTIVE   = 1
STEP_RUNNING  = 2
STEP_DONE     = 3
STEP_ERROR    = 4

_STATE_STYLES = {
    STEP_PENDING: "QFrame { border: 2px solid #555; border-radius: 6px; background: #2b2b2b; }",
    STEP_ACTIVE:  "QFrame { border: 2px solid #4A9EFF; border-radius: 6px; background: #1e3550; }",
    STEP_RUNNING: "QFrame { border: 2px solid #F0A500; border-radius: 6px; background: #3a2e00; }",
    STEP_DONE:    "QFrame { border: 2px solid #4CAF50; border-radius: 6px; background: #1b3a1e; }",
    STEP_ERROR:   "QFrame { border: 2px solid #F44336; border-radius: 6px; background: #3a1515; }",
}

_STATE_BADGE = {
    STEP_PENDING:  ("●", "#888888"),
    STEP_ACTIVE:   ("●", "#4A9EFF"),
    STEP_RUNNING:  ("◉", "#F0A500"),
    STEP_DONE:     ("✔", "#4CAF50"),
    STEP_ERROR:    ("✖", "#F44336"),
}


# ---------------------------------------------------------------------------
# StepBox — one card in the flowchart sidebar
# ---------------------------------------------------------------------------
class StepBox(QFrame):
    clicked = pyqtSignal(int)  # emits the step index

    def __init__(self, index: int, step: dict, parent=None):
        super().__init__(parent)
        self._index = index
        self._state = STEP_PENDING

        self.setFixedHeight(76)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_STATE_STYLES[STEP_PENDING])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._badge = QLabel("●")
        self._badge.setFixedWidth(16)
        font_badge = QFont()
        font_badge.setPointSize(13)
        self._badge.setFont(font_badge)
        self._badge.setStyleSheet(f"color: #888888; border: none; background: transparent;")

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self._id_label = QLabel(step["id"])
        font_id = QFont()
        font_id.setPointSize(12)
        font_id.setBold(True)
        self._id_label.setFont(font_id)
        self._id_label.setFixedHeight(self._id_label.fontMetrics().height())
        self._id_label.setStyleSheet("color: #aaaaaa; border: none; background: transparent; margin: 0; padding: 0;")

        self._title_label = QLabel(step["title"])
        font_title = QFont()
        font_title.setPointSize(14)
        self._title_label.setFont(font_title)
        self._title_label.setFixedHeight(self._title_label.fontMetrics().height())
        self._title_label.setStyleSheet("color: #dddddd; border: none; background: transparent; margin: 0; padding: 0;")

        text_layout.addWidget(self._id_label)
        text_layout.addWidget(self._title_label)

        layout.addWidget(self._badge)
        layout.addLayout(text_layout)

    def set_state(self, state: int):
        self._state = state
        self.setStyleSheet(_STATE_STYLES[state])
        icon, color = _STATE_BADGE[state]
        self._badge.setText(icon)
        self._badge.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        if state == STEP_ACTIVE:
            self._title_label.setStyleSheet("color: #ffffff; font-weight: bold; border: none; background: transparent;")
        else:
            self._title_label.setStyleSheet("color: #dddddd; border: none; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Arrow connector label between step boxes
# ---------------------------------------------------------------------------
class _ArrowLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__("▼", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(16)
        self.setStyleSheet("color: #555555; font-size: 10px; background: transparent;")


# ---------------------------------------------------------------------------
# FlowchartPanel — resizable left sidebar with pinned footer
# ---------------------------------------------------------------------------
class FlowchartPanel(QWidget):
    step_selected = pyqtSignal(int)
    run_all_requested = pyqtSignal()

    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setStyleSheet("background: #1e1e1e;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scrollable step list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #1e1e1e; }"
            + theme.SCROLLBAR
        )

        self._step_boxes: list[StepBox] = []
        container = QWidget()
        container.setStyleSheet("background: #1e1e1e;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(0)

        header = QLabel("Pipeline Steps")
        font_h = QFont()
        font_h.setPointSize(15)
        font_h.setBold(True)
        header.setFont(font_h)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #dddddd; padding-bottom: 10px; background: transparent;")
        layout.addWidget(header)

        for i, step in enumerate(steps):
            box = StepBox(i, step)
            box.clicked.connect(self.step_selected)
            self._step_boxes.append(box)
            layout.addWidget(box)
            if i < len(steps) - 1:
                layout.addWidget(_ArrowLabel())

        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

        # Pinned footer — always visible regardless of scroll position
        footer = QWidget()
        footer.setStyleSheet("background: #1e1e1e; border-top: 1px solid #3a3a3a;")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(8, 8, 8, 8)

        self.run_all_btn = QPushButton("▶▶  Run All Steps")
        self.run_all_btn.setFixedHeight(34)
        self.run_all_btn.setStyleSheet(theme.BTN_RUN_ALL)
        self.run_all_btn.clicked.connect(self.run_all_requested)
        footer_layout.addWidget(self.run_all_btn)

        outer.addWidget(footer)

    def set_active(self, index: int):
        for i, box in enumerate(self._step_boxes):
            if box._state not in (STEP_DONE, STEP_ERROR, STEP_RUNNING):
                box.set_state(STEP_ACTIVE if i == index else STEP_PENDING)

    def set_step_state(self, index: int, state: int):
        if 0 <= index < len(self._step_boxes):
            self._step_boxes[index].set_state(state)

    def reset(self):
        for box in self._step_boxes:
            box.set_state(STEP_PENDING)


# ---------------------------------------------------------------------------
# OutputTab — shows step output; data-driven from the registry output spec
# ---------------------------------------------------------------------------

class OutputTab(QWidget):
    """
    Two states:
      • _has_run = False  → prompt the user to run the step first.
      • _has_run = True   → render content according to the registry output spec.

    For type "side_by_side" the panels are resolved at render time using the
    current arg values supplied via set_values_getter().
    """

    def __init__(self, output_spec: dict | None, parent=None):
        super().__init__(parent)
        self._spec = output_spec          # dict from registry, or None
        self._get_values = None           # callable() → dict[str, Any]
        self._has_run = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(6)

        # Refresh button (top-right)
        top_row = QHBoxLayout()
        top_row.addStretch()
        self._refresh_btn = QPushButton("↻  Refresh")
        self._refresh_btn.setFixedWidth(86)
        self._refresh_btn.setFixedHeight(24)
        self._refresh_btn.setStyleSheet(theme.BTN_SECONDARY)
        self._refresh_btn.clicked.connect(self.refresh)
        top_row.addWidget(self._refresh_btn)
        outer.addLayout(top_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet(theme.SCROLL_AREA)
        outer.addWidget(self._scroll)

        output_renderers.show_message(self._scroll, "Run the step first to see output here.")

    # ------------------------------------------------------------------
    def set_values_getter(self, fn):
        """Supply a callable that returns the current form field values."""
        self._get_values = fn

    def mark_run(self):
        """Called externally when the step finishes successfully."""
        self._has_run = True
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        if not self._has_run:
            output_renderers.show_message(self._scroll, "Run the step first to see output here.")
            return

        if not self._spec or self._spec.get("type") == "none":
            output_renderers.show_message(self._scroll, "No output configured for this step.")
            return

        values = self._get_values() if self._get_values else {}
        if self._spec.get("type") == "side_by_side":
            output_renderers.render_side_by_side(self._scroll, self._spec, values)
        elif self._spec.get("type") == "single_image":
            output_renderers.render_single_image(self._scroll, self._spec, values)



# ---------------------------------------------------------------------------
# StepFormPage — dynamic form for one pipeline step
# ---------------------------------------------------------------------------
class StepFormPage(QWidget):
    def __init__(self, step: dict, shared_store: dict, parent=None):
        super().__init__(parent)
        self._step = step
        self._shared_store = shared_store  # mutable dict shared across all pages
        self._fields: dict[str, QWidget] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(theme.TAB_WIDGET)

        # ── Configure tab ────────────────────────────────────────────────────
        config_widget = QWidget()
        config_widget.setStyleSheet("background: #1e1e1e;")
        config_outer = QVBoxLayout(config_widget)
        config_outer.setContentsMargins(20, 16, 20, 16)
        config_outer.setSpacing(12)

        # Step header
        id_label = QLabel(f"Step {step['id']}")
        font_id = QFont()
        font_id.setPointSize(14)
        font_id.setBold(True)
        id_label.setFont(font_id)
        id_label.setStyleSheet("color: #4A9EFF;")

        title_label = QLabel(step["title"])
        font_title = QFont()
        font_title.setPointSize(14)
        font_title.setBold(True)
        title_label.setFont(font_title)

        desc_label = QLabel(step["description"])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444444;")

        config_outer.addWidget(id_label)
        config_outer.addWidget(title_label)
        config_outer.addWidget(desc_label)
        config_outer.addWidget(sep)

        # Argument fields inside a scroll area so they never clip on small windows
        form_widget = QWidget()
        form_widget.setStyleSheet("background: #1e1e1e;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(0, 4, 0, 4)

        for arg in step["args"]:
            row = self._make_field(arg)
            form_layout.addLayout(row)
        form_layout.addStretch()

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        form_scroll.setWidget(form_widget)
        form_scroll.setStyleSheet(
            "QScrollArea { border: none; background: #1e1e1e; }" + theme.SCROLLBAR
        )
        config_outer.addWidget(form_scroll)

        # Run button
        self.run_btn = QPushButton(f"▶  Run Step {step['id']}: {step['title']}")
        self.run_btn.setFixedHeight(36)
        self.run_btn.setStyleSheet(theme.BTN_PRIMARY)
        config_outer.addWidget(self.run_btn)

        # ── Output tab ───────────────────────────────────────────────────────
        self._output_tab = OutputTab(step.get("output"))
        self._output_tab.set_values_getter(self.get_values)

        self._tabs.addTab(config_widget, "  Configure  ")
        self._tabs.addTab(self._output_tab, "  Output  ")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        outer.addWidget(self._tabs)

    def _on_tab_changed(self, index: int):
        if index == 1:
            self._output_tab.refresh()

    def refresh_output(self):
        """Called externally when the step finishes successfully."""
        self._output_tab.mark_run()

    def _make_field(self, arg: dict):
        row = QVBoxLayout()
        row.setSpacing(3)

        lbl = QLabel(arg["label"] + (" *" if arg["required"] else ""))
        lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        row.addWidget(lbl)

        if arg["type"] == "bool":
            widget = QCheckBox(arg["label"])
            widget.setChecked(bool(arg.get("default", False)))
            widget.setToolTip(arg.get("help", ""))
            widget.setStyleSheet("font-size: 11px; color: #cccccc;")
            row.addWidget(widget)

        elif arg["type"] in ("path_dir", "path_file"):
            h = QHBoxLayout()
            h.setSpacing(6)
            line = QLineEdit()
            line.setPlaceholderText(arg.get("help", ""))
            line.setToolTip(arg.get("help", ""))
            line.setText(str(arg.get("default", "")))
            line.setStyleSheet(theme.INPUT)
            browse_btn = QPushButton("Browse…")
            browse_btn.setFixedWidth(72)
            browse_btn.setStyleSheet(theme.BTN_SECONDARY)
            is_dir = arg["type"] == "path_dir"
            browse_btn.clicked.connect(lambda checked, w=line, d=is_dir: self._browse(w, d))
            h.addWidget(line)
            h.addWidget(browse_btn)
            row.addLayout(h)
            widget = line

        elif arg["type"] == "int":
            widget = QLineEdit()
            widget.setPlaceholderText(arg.get("help", ""))
            widget.setToolTip(arg.get("help", ""))
            widget.setText(str(arg.get("default", "")))
            widget.setValidator(QIntValidator())
            widget.setFixedWidth(100)
            widget.setStyleSheet(theme.INPUT)
            h_int = QHBoxLayout()
            h_int.setContentsMargins(0, 0, 0, 0)
            h_int.addWidget(widget)
            h_int.addStretch()
            row.addLayout(h_int)

        elif arg["type"] == "float":
            widget = QLineEdit()
            widget.setPlaceholderText(arg.get("help", ""))
            widget.setToolTip(arg.get("help", ""))
            widget.setText(str(arg.get("default", "")))
            widget.setValidator(QDoubleValidator())
            widget.setFixedWidth(120)
            widget.setStyleSheet(theme.INPUT)
            h_float = QHBoxLayout()
            h_float.setContentsMargins(0, 0, 0, 0)
            h_float.addWidget(widget)
            h_float.addStretch()
            row.addLayout(h_float)

        else:
            widget = QLineEdit()
            row.addWidget(widget)

        self._fields[arg["name"]] = widget

        # On change: write-through to shared_store for positional args
        if arg.get("positional"):
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda val, n=arg["name"]: self._shared_store.update({n: val}))
            elif isinstance(widget, QCheckBox):
                widget.toggled.connect(lambda checked, n=arg["name"]: self._shared_store.update({n: checked}))

        return row

    def _browse(self, line_edit: QLineEdit, is_dir: bool):
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text() or os.path.expanduser("~"))
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select File", line_edit.text() or os.path.expanduser("~"))
        if path:
            line_edit.setText(path)

    def get_values(self) -> dict:
        values = {}
        for arg in self._step["args"]:
            widget = self._fields[arg["name"]]
            if isinstance(widget, QCheckBox):
                values[arg["name"]] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                values[arg["name"]] = widget.text().strip()
        return values

    def validate(self) -> list[str]:
        errors = []
        values = self.get_values()
        for arg in self._step["args"]:
            if arg.get("required") and not values.get(arg["name"]):
                errors.append(f"'{arg['label']}' is required.")
        return errors

    def sync_from_store(self):
        """Populate shared positional fields from the shared store (used when switching pages)."""
        for arg in self._step["args"]:
            if arg.get("positional") and arg["name"] in self._shared_store:
                widget = self._fields[arg["name"]]
                val = self._shared_store[arg["name"]]
                if isinstance(widget, QLineEdit) and widget.text() != str(val):
                    widget.blockSignals(True)
                    widget.setText(str(val))
                    widget.blockSignals(False)


# ---------------------------------------------------------------------------
# LogPanel — live scrollable output
# ---------------------------------------------------------------------------
class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(34)
        self._collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)

        header_row = QHBoxLayout()

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(22, 22)
        self._toggle_btn.setToolTip("Collapse / expand log")
        self._toggle_btn.setStyleSheet(theme.BTN_SMALL)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        header_row.addWidget(self._toggle_btn)

        lbl = QLabel("Output Log")
        font_lbl = QFont()
        font_lbl.setPointSize(11)
        font_lbl.setBold(True)
        lbl.setFont(font_lbl)
        lbl.setStyleSheet("color: #888888;")
        header_row.addWidget(lbl)
        header_row.addStretch()

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setFixedHeight(22)
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setStyleSheet(theme.BTN_STOP)
        self.stop_btn.setVisible(False)
        header_row.addWidget(self.stop_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(52)
        clear_btn.setFixedHeight(22)
        clear_btn.setStyleSheet(theme.BTN_SMALL)
        clear_btn.clicked.connect(self.clear)
        header_row.addWidget(clear_btn)

        layout.addLayout(header_row)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        mono = QFont("Menlo")
        if not mono.exactMatch():
            mono = QFont("Courier New")
        mono.setPointSize(12)
        self._text.setFont(mono)
        self._text.setStyleSheet(
            "QTextEdit { background: #141414; color: #cccccc; border: 1px solid #444; border-radius: 4px; padding: 4px; }"
        )
        layout.addWidget(self._text)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self._text.setVisible(not self._collapsed)
        self._toggle_btn.setText("▶" if self._collapsed else "▼")
        self.setMaximumHeight(38 if self._collapsed else 16777215)

    def append_text(self, text: str, color: str = "#cccccc"):
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._text.append(f'<span style="color:{color};">{escaped}</span>')
        self._text.verticalScrollBar().setValue(self._text.verticalScrollBar().maximum())

    def append_stdout(self, text: str):  self.append_text(text, "#cccccc")
    def append_stderr(self, text: str):  self.append_text(text, "#F0A500")
    def append_info(self, text: str):    self.append_text(text, "#4A9EFF")
    def append_success(self, text: str): self.append_text(text, "#4CAF50")
    def append_error(self, text: str):   self.append_text(text, "#F44336")

    def clear(self):
        self._text.clear()


# ---------------------------------------------------------------------------
# ProfileBar — top bar with profile selector and Run All
# ---------------------------------------------------------------------------
class ProfileBar(QWidget):
    profile_changed = pyqtSignal(str)

    _PILL_ACTIVE = (
        "QPushButton { background: #4A9EFF; color: #ffffff; border: none; "
        "border-radius: 14px; padding: 4px 16px; font-size: 12px; font-weight: bold; }"
    )
    _PILL_INACTIVE = (
        "QPushButton { background: #2b2b2b; color: #888888; border: 1px solid #444; "
        "border-radius: 14px; padding: 4px 16px; font-size: 12px; }"
        "QPushButton:hover { background: #3a3a3a; color: #cccccc; }"
    )
    _PILL_CUSTOM_IDLE = (
        "QPushButton { background: #1e1e1e; color: #888888; border: 1px dashed #666; "
        "border-radius: 14px; padding: 4px 16px; font-size: 12px; }"
        "QPushButton:hover { background: #2b2b2b; color: #cccccc; border-color: #4A9EFF; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet("background: #1e1e1e;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # "Profile:" label
        lbl = QLabel("Profile:")
        lbl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl)
        layout.addSpacing(2)

        self._pill_buttons: dict[str, QPushButton] = {}
        self._active_profile: str = ""
        self._custom_loaded_name: str = ""   # name from the last loaded custom JSON

        for name in PROFILES.keys():
            btn = QPushButton(name)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self._select(n))
            self._pill_buttons[name] = btn
            layout.addWidget(btn)

        # Custom browse pill
        self._custom_btn = QPushButton("⊕  Custom…")
        self._custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._custom_btn.setStyleSheet(self._PILL_CUSTOM_IDLE)
        self._custom_btn.clicked.connect(self._browse_custom)
        layout.addWidget(self._custom_btn)

        # Activate first built-in profile
        first = next(iter(PROFILES))
        self._active_profile = first
        for name, btn in self._pill_buttons.items():
            btn.setStyleSheet(self._PILL_ACTIVE if name == first else self._PILL_INACTIVE)

        layout.addStretch()

    def _select(self, name: str):
        if name == self._active_profile:
            return
        self._active_profile = name
        for n, btn in self._pill_buttons.items():
            btn.setStyleSheet(self._PILL_ACTIVE if n == name else self._PILL_INACTIVE)
        # Reset custom pill to idle (dimmed if a file was previously loaded, dashed if not)
        self._custom_btn.setStyleSheet(
            self._PILL_INACTIVE if self._custom_loaded_name else self._PILL_CUSTOM_IDLE
        )
        self.profile_changed.emit(name)

    def _browse_custom(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Custom Profile", os.path.expanduser("~"), "Profile JSON (*.json)"
        )
        if not path:
            return
        try:
            name, profile = _load_profile_from_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Failed to load profile", str(exc))
            return

        # Register dynamically so MainWindow can look it up by name
        PROFILES[name] = profile
        self._custom_loaded_name = name

        # Update custom pill to look active with the profile's name
        self._custom_btn.setText(name)
        self._custom_btn.setStyleSheet(self._PILL_ACTIVE)

        # Deactivate all built-in pills
        for btn in self._pill_buttons.values():
            btn.setStyleSheet(self._PILL_INACTIVE)

        self._active_profile = name
        self.profile_changed.emit(name)

    def current_profile(self) -> str:
        return self._active_profile


# ---------------------------------------------------------------------------
# GripSplitter — vertical splitter with a visible grip handle
# ---------------------------------------------------------------------------
class _GripHandle(QSplitterHandle):
    """Paints three short horizontal lines centred on the handle."""

    _LINE_COLOR  = QColor("#666666")
    _HOVER_COLOR = QColor("#4A9EFF")
    _LINE_W      = 24
    _LINE_GAP    = 3

    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self._hovered = False
        self.setCursor(Qt.CursorShape.SplitVCursor)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor("#4A9EFF" if self._hovered else "#3a3a3a")
        painter.fillRect(self.rect(), bg)

        pen = QPen(self._HOVER_COLOR if self._hovered else self._LINE_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)

        cx = self.width() // 2
        cy = self.height() // 2
        half_w = self._LINE_W // 2
        for offset in (-self._LINE_GAP, 0, self._LINE_GAP):
            painter.drawLine(cx - half_w, cy + offset, cx + half_w, cy + offset)

        painter.end()


class GripSplitter(QSplitter):
    def createHandle(self):
        return _GripHandle(self.orientation(), self)


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("eROSuite")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        if _profile_load_errors:
            QMessageBox.critical(
                None, "Profile load error",
                "One or more built-in profiles failed to load:\n" + "\n".join(_profile_load_errors)
            )
            sys.exit(1)

        # Dark palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#dddddd"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2b2b2b"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#dddddd"))
        QApplication.instance().setPalette(palette)

        self._process: QProcess | None = None
        self._current_step_index: int = 0
        self._run_all_queue: list[int] = []
        self._shared_store: dict = {}

        self._profile_bar = ProfileBar()
        self._profile_bar.profile_changed.connect(self._on_profile_changed)

        # Build initial profile UI
        initial_profile = self._profile_bar.current_profile()
        self._steps = PROFILES[initial_profile]["steps"]

        self._flowchart = FlowchartPanel(self._steps)
        self._flowchart.step_selected.connect(self._on_step_selected)
        self._flowchart.run_all_requested.connect(self._on_run_all)

        self._step_widget = QStackedWidget()
        self._pages: list[StepFormPage] = []
        self._build_step_pages()

        # Right-side layout: profile bar + separator + stacked pages + log
        right_widget = QWidget()
        right_widget.setStyleSheet("background: #1e1e1e;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._profile_bar)

        # Thin separator below profile bar (fix #21)
        profile_sep = QFrame()
        profile_sep.setFrameShape(QFrame.Shape.HLine)
        profile_sep.setMaximumHeight(1)
        profile_sep.setStyleSheet("color: #3a3a3a;")
        right_layout.addWidget(profile_sep)

        step_wrapper = QWidget()
        step_wrapper.setStyleSheet("background: #1e1e1e;")
        sw_layout = QVBoxLayout(step_wrapper)
        sw_layout.setContentsMargins(8, 0, 8, 0)
        sw_layout.setSpacing(0)
        sw_layout.addWidget(self._step_widget)

        self._log_panel = LogPanel()
        self._log_panel.setStyleSheet("background: #1e1e1e; padding: 0 8px 0 8px;")
        self._log_panel.stop_btn.clicked.connect(self._on_stop)

        content_splitter = GripSplitter(Qt.Orientation.Vertical)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(7)
        content_splitter.addWidget(step_wrapper)
        content_splitter.addWidget(self._log_panel)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([540, 260])

        right_layout.addWidget(content_splitter)

        # Root layout: sidebar + separator + right
        root = QWidget()
        root.setStyleSheet("background: #1e1e1e;")
        self._root_layout = QHBoxLayout(root)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)
        self._root_layout.addWidget(self._flowchart)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #3a3a3a;")
        self._root_layout.addWidget(sep)

        self._root_layout.addWidget(right_widget)

        self.setCentralWidget(root)

        self.statusBar().setStyleSheet(
            "QStatusBar { background: #252525; color: #888888; font-size: 11px;"
            " border-top: 1px solid #3a3a3a; }"
        )
        self.statusBar().showMessage("Ready")

        # Select first step
        self._select_step(0)

    # ------------------------------------------------------------------
    # Profile helpers
    # ------------------------------------------------------------------

    def _build_step_pages(self):
        self._pages.clear()
        while self._step_widget.count():
            w = self._step_widget.widget(0)
            self._step_widget.removeWidget(w)
        for step in self._steps:
            page = StepFormPage(step, self._shared_store)
            page.run_btn.clicked.connect(lambda checked, s=step: self._on_run_step(s))
            self._pages.append(page)
            self._step_widget.addWidget(page)

    def _on_profile_changed(self, profile_name: str):
        self._shared_store.clear()
        self._steps = PROFILES[profile_name]["steps"]

        # Rebuild sidebar
        self._flowchart.deleteLater()
        self._flowchart = FlowchartPanel(self._steps)
        self._flowchart.step_selected.connect(self._on_step_selected)
        self._flowchart.run_all_requested.connect(self._on_run_all)

        # Swap sidebar in root layout
        old_flowchart = self._root_layout.itemAt(0).widget()
        self._root_layout.replaceWidget(old_flowchart, self._flowchart)
        old_flowchart.deleteLater()

        # Rebuild pages
        self._build_step_pages()
        self._select_step(0)

        self._log_panel.append_info(f"Profile switched to: {profile_name}")
        self.statusBar().showMessage(f"Profile: {profile_name}")

    # ------------------------------------------------------------------
    # Step navigation
    # ------------------------------------------------------------------

    def _select_step(self, index: int):
        self._current_step_index = index
        self._step_widget.setCurrentIndex(index)
        self._flowchart.set_active(index)
        self._pages[index].sync_from_store()
        step = self._steps[index]
        self.statusBar().showMessage(f"Step {step['id']}: {step['title']}")

    def _on_step_selected(self, index: int):
        self._select_step(index)

    # ------------------------------------------------------------------
    # Collect CLI args from a page
    # ------------------------------------------------------------------

    def _build_command(self, page: StepFormPage) -> list[str]:
        script = page._step["script"]
        values = page.get_values()
        step = page._step

        positional_args = []
        flag_args = []

        for arg in step["args"]:
            if arg.get("positional"):
                positional_args.append(values.get(arg["name"], ""))
            else:
                if arg["type"] == "bool":
                    checked = values.get(arg["name"], False)
                    if arg.get("flag_inverted"):
                        if not checked:
                            flag_args.append(arg["flag"])
                    elif checked:
                        flag_args.append(arg["flag"])
                else:
                    val = values.get(arg["name"], "")
                    if val:
                        flag_args.extend([arg["flag"], val])

        return [sys.executable, script] + positional_args + flag_args

    # ------------------------------------------------------------------
    # Run a single step
    # ------------------------------------------------------------------

    def _on_run_step(self, step: dict):
        step_index = next(i for i, s in enumerate(self._steps) if s["id"] == step["id"])
        page = self._pages[step_index]

        errors = page.validate()
        if errors:
            QMessageBox.warning(self, "Missing required fields", "\n".join(errors))
            return

        cmd = self._build_command(page)
        self._run_command(cmd, step_index)

    # ------------------------------------------------------------------
    # Run All
    # ------------------------------------------------------------------

    def _on_run_all(self):
        # Validate all pages first
        all_errors = []
        for i, page in enumerate(self._pages):
            page.sync_from_store()
            errs = page.validate()
            for e in errs:
                all_errors.append(f"Step {self._steps[i]['id']}: {e}")
        if all_errors:
            QMessageBox.warning(self, "Missing required fields", "\n".join(all_errors))
            return

        # Queue all steps; Run All runs the last step's command (full pipeline)
        # Since Setup.py is monolithic, running with all args once covers all steps.
        # We queue each step for UX state tracking, but subprocess is called once per step.
        self._run_all_queue = list(range(len(self._steps)))
        self._advance_run_all_queue()

    def _advance_run_all_queue(self):
        if not self._run_all_queue:
            self._log_panel.append_success("=== All steps completed ===")
            return
        step_index = self._run_all_queue.pop(0)
        self._select_step(step_index)
        page = self._pages[step_index]
        page.sync_from_store()
        cmd = self._build_command(page)
        self._run_command(cmd, step_index, on_success=self._advance_run_all_queue)

    # ------------------------------------------------------------------
    # QProcess execution
    # ------------------------------------------------------------------

    def _run_command(self, cmd: list[str], step_index: int, on_success=None):
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "Already running", "A step is already running. Please wait for it to finish.")
            return

        self._select_step(step_index)
        self._flowchart.set_step_state(step_index, STEP_RUNNING)
        self._flowchart.run_all_btn.setEnabled(False)
        for page in self._pages:
            page.run_btn.setEnabled(False)

        self._log_panel.stop_btn.setVisible(True)
        self._log_panel.append_info(f"\n$ {' '.join(cmd)}\n")
        self.statusBar().showMessage(f"Running step {self._steps[step_index]['id']}\u2026")

        self._process = QProcess(self)
        self._process.setProgram(cmd[0])
        self._process.setArguments(cmd[1:])
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        self._process.readyReadStandardOutput.connect(
            lambda: self._on_stdout(step_index)
        )
        self._process.finished.connect(
            lambda exit_code, exit_status, si=step_index, cb=on_success:
                self._on_process_finished(exit_code, exit_status, si, cb)
        )

        self._process.start()

    def _on_stop(self):
        self._run_all_queue.clear()
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        self._log_panel.append_error("\u25a0 Step stopped by user.")

    def _on_stdout(self, step_index: int):
        if self._process:
            raw = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
            for line in raw.splitlines():
                self._log_panel.append_stdout(line)

    def _on_process_finished(self, exit_code: int, exit_status, step_index: int, on_success=None):
        self._log_panel.stop_btn.setVisible(False)
        if exit_code == 0:
            self._flowchart.set_step_state(step_index, STEP_DONE)
            self._log_panel.append_success(f"\n✔ Step {self._steps[step_index]['id']} finished successfully (exit code 0)")
            self.statusBar().showMessage(f"Step {self._steps[step_index]['id']} completed successfully")
            # Refresh the output tab so new files appear immediately
            self._pages[step_index].refresh_output()
        else:
            self._flowchart.set_step_state(step_index, STEP_ERROR)
            self._log_panel.append_error(f"\n✖ Step {self._steps[step_index]['id']} failed (exit code {exit_code})")
            self.statusBar().showMessage(f"Step {self._steps[step_index]['id']} failed (exit code {exit_code})")
            self._run_all_queue.clear()

        self._flowchart.run_all_btn.setEnabled(True)
        for page in self._pages:
            page.run_btn.setEnabled(True)

        self._process = None

        if exit_code == 0 and on_success:
            on_success()


# ---------------------------------------------------------------------------
# App Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

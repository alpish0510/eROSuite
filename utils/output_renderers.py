"""
output_renderers.py
-------------------
All output-rendering functions for eROSuite.

Each public function follows the signature:
    render_<type>(scroll_area: QScrollArea, spec: dict, values: dict) -> None

Add new renderer functions here as additional output types are introduced
(e.g. render_fits_image, render_table, …).  The dispatcher in OutputTab.refresh()
just needs a matching entry added to its if/elif chain.
"""

import os
import glob as _glob

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _ScalableImageLabel(QLabel):
    """A QLabel that always scales its pixmap to fill its current size."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._orig = pixmap
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMinimumSize(1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scaled()

    def _apply_scaled(self):
        if self._orig.isNull():
            return
        scaled = self._orig.scaled(
            self.width(), self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def show_message(scroll_area: QScrollArea, msg: str, color: str = "#555555") -> None:
    """Replace the scroll area's content with a centred plain-text message."""
    lbl = QLabel(msg)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {color}; font-size: 13px; background: transparent;"
    )
    scroll_area.setWidget(lbl)


def _collect_images(panel: dict, values: dict) -> list[str]:
    """Return a sorted list of image paths for one panel spec."""
    dir_val = values.get(panel.get("dir_arg", ""), "").strip()
    if not dir_val:
        return []
    subdir = panel.get("subdir", "")
    scan_dir = os.path.join(dir_val, subdir) if subdir else dir_val
    if not os.path.isdir(scan_dir):
        return []
    pattern = os.path.join(scan_dir, panel.get("glob", "*.png"))
    return sorted(_glob.glob(pattern))


# ---------------------------------------------------------------------------
# Renderer: side_by_side
# ---------------------------------------------------------------------------

def render_side_by_side(
    scroll_area: QScrollArea, spec: dict, values: dict
) -> None:
    """
    Render two (or more) image columns side by side inside *scroll_area*.

    Registry spec keys:
        panels  - list of panel dicts, each with:
            label         - column header string
            dir_arg       - form-field key whose value is the root directory
            subdir        - (optional) subdirectory appended to dir_arg value
            glob          - (optional) glob pattern for images, default "*.png"
            condition_arg - (optional) form-field key; panel hidden when falsy
    """
    panels_spec: list[dict] = spec.get("panels", [])

    active = [
        p for p in panels_spec
        if not p.get("condition_arg") or values.get(p["condition_arg"])
    ]

    if not active:
        show_message(scroll_area, "No output panels active for current settings.")
        return

    panel_images: list[list[str]] = [_collect_images(p, values) for p in active]

    total = sum(len(imgs) for imgs in panel_images)
    if total == 0:
        show_message(
            scroll_area,
            "No images found yet.\nRun the step to generate output.",
        )
        return

    n_cols = len(active)
    col_img_w = 400 #if n_cols >= 2 else 620

    container = QWidget()
    container.setStyleSheet("background: #141414;")
    vbox = QVBoxLayout(container)
    vbox.setContentsMargins(12, 12, 12, 12)
    vbox.setSpacing(10)

    # Column headers
    hdr_row = QHBoxLayout()
    hdr_row.setSpacing(8)
    for i, p in enumerate(active):
        hdr = QLabel(f"{p['label']}  ({len(panel_images[i])})")
        font_h = QFont()
        font_h.setPointSize(12)
        font_h.setBold(True)
        hdr.setFont(font_h)
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet(
            "color: #4A9EFF; background: transparent; padding: 4px 0;"
        )
        hdr_row.addWidget(hdr, 1)
    vbox.addLayout(hdr_row)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: #333333;")
    vbox.addWidget(sep)

    # One row per image index, paired across all panels
    max_rows = max(len(imgs) for imgs in panel_images)
    for row_i in range(max_rows):
        row_h = QHBoxLayout()
        row_h.setSpacing(8)

        for imgs in panel_images:
            cell = QWidget()
            cell.setStyleSheet("background: transparent;")
            cell_v = QVBoxLayout(cell)
            cell_v.setContentsMargins(0, 0, 0, 0)
            cell_v.setSpacing(3)

            if row_i < len(imgs):
                img_path = imgs[row_i]

                name_lbl = QLabel(os.path.basename(img_path))
                name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                name_lbl.setStyleSheet(
                    "color: #ffffff; font-size: 12px; background: transparent;"
                )
                cell_v.addWidget(name_lbl)

                pix = QPixmap(img_path)
                if not pix.isNull():
                    scaled = pix.scaledToWidth(
                        min(pix.width(), col_img_w),
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    img_lbl = QLabel()
                    img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    img_lbl.setPixmap(scaled)
                    img_lbl.setStyleSheet("background: transparent;")
                    cell_v.addWidget(img_lbl)
                else:
                    err = QLabel(
                        f"[Could not load: {os.path.basename(img_path)}]"
                    )
                    err.setStyleSheet(
                        "color: #F44336; font-size: 10px; background: transparent;"
                    )
                    cell_v.addWidget(err)
            else:
                cell_v.addStretch()

            row_h.addWidget(cell, 1)

        vbox.addLayout(row_h)

        if row_i < max_rows - 1:
            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setStyleSheet("color: #2a2a2a;")
            vbox.addWidget(div)

    vbox.addStretch()
    scroll_area.setWidget(container)


# ---------------------------------------------------------------------------
# Renderer: single_image
# ---------------------------------------------------------------------------

def render_single_image(
    scroll_area: QScrollArea, spec: dict, values: dict
) -> None:
    """
    Render a single, known image file inside *scroll_area*.

    Registry spec keys:
        dir_arg  - form-field key whose value is the root directory
        filename - fixed filename inside that directory
        label    - (optional) caption shown above the image
    """
    dir_val = values.get(spec.get("dir_arg", ""), "").strip()
    if not dir_val:
        show_message(scroll_area, "Output directory not set.")
        return

    img_path = os.path.join(dir_val, spec.get("filename", ""))
    if not os.path.isfile(img_path):
        show_message(
            scroll_area,
            "No image found yet.\nRun the step with Generate Tile Footprint to generate output.",
        )
        return

    container = QWidget()
    container.setStyleSheet("background: #141414;")
    vbox = QVBoxLayout(container)
    vbox.setContentsMargins(12, 12, 12, 12)
    vbox.setSpacing(8)

    caption = spec.get("label") or os.path.basename(img_path)
    hdr = QLabel(caption)
    font_h = QFont()
    font_h.setPointSize(15)
    font_h.setBold(True)
    hdr.setFont(font_h)
    hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hdr.setStyleSheet("color: #4A9EFF; background: transparent; padding: 4px 0;")
    vbox.addWidget(hdr)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: #333333;")
    vbox.addWidget(sep)

    pix = QPixmap(img_path)
    if pix.isNull():
        show_message(scroll_area, f"Could not load image:\n{img_path}", color="#F44336")
        return

    img_lbl = _ScalableImageLabel(pix)
    vbox.addWidget(img_lbl, stretch=1)

    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(container)

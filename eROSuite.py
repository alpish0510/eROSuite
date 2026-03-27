import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QPushButton, QVBoxLayout, QLabel
)


# -------------------------
# Galaxy Cluster Tab
# -------------------------
class ClusterTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.label = QLabel("Cluster analysis tools go here")
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.clicked.connect(self.run_analysis)

        layout.addWidget(self.label)
        layout.addWidget(self.run_btn)
        layout.addStretch()

        self.setLayout(layout)

    def run_analysis(self):
        print("Running cluster analysis...")


# -------------------------
# SNR Tab
# -------------------------
class SNRTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.label = QLabel("SNR tools go here")
        self.run_btn = QPushButton("Compute SNR")
        self.run_btn.clicked.connect(self.compute_snr)

        layout.addWidget(self.label)
        layout.addWidget(self.run_btn)
        layout.addStretch()

        self.setLayout(layout)

    def compute_snr(self):
        print("Computing SNR...")


# -------------------------
# Main Window
# -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("eROSuite")
        self.resize(800, 600)

        tabs = QTabWidget()
        tabs.addTab(ClusterTab(), "Galaxy Cluster Analysis")
        tabs.addTab(SNRTab(), "Supernova Remnant Analysis")

        self.setCentralWidget(tabs)


# -------------------------
# App Entry Point
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton,
    QVBoxLayout, QLabel
)


# -------------------------
# Cluster Window
# -------------------------
class ClusterWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Cluster Analysis")

        layout = QVBoxLayout()

        self.label = QLabel("Cluster analysis tools go here")
        self.run_btn = QPushButton("Run Analysis")

        self.run_btn.clicked.connect(self.run_analysis)

        layout.addWidget(self.label)
        layout.addWidget(self.run_btn)

        self.setLayout(layout)

    def run_analysis(self):
        print("Running cluster analysis...")


# -------------------------
# SNR Window
# -------------------------
class SNRWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SNR Analysis")

        layout = QVBoxLayout()

        self.label = QLabel("SNR tools go here")
        self.run_btn = QPushButton("Compute SNR")

        self.run_btn.clicked.connect(self.compute_snr)

        layout.addWidget(self.label)
        layout.addWidget(self.run_btn)

        self.setLayout(layout)

    def compute_snr(self):
        print("Computing SNR...")


# -------------------------
# Main Window
# -------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Astro Analysis Toolkit")

        layout = QVBoxLayout()

        self.cluster_btn = QPushButton("Cluster Analysis")
        self.snr_btn = QPushButton("SNR Analysis")

        layout.addWidget(self.cluster_btn)
        layout.addWidget(self.snr_btn)

        self.setLayout(layout)

        # Create child windows (important: keep references!)
        self.cluster_window = ClusterWindow()
        self.snr_window = SNRWindow()

        # Connect buttons
        self.cluster_btn.clicked.connect(self.open_cluster)
        self.snr_btn.clicked.connect(self.open_snr)

    def open_cluster(self):
        self.cluster_window.show()

    def open_snr(self):
        self.snr_window.show()


# -------------------------
# App Entry Point
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
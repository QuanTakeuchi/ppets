"""
Launches the PPETS Visualization layer (LLD §3): ConfigPanel, GridView,
ChartView, playback controls, and live stats, wired through
SimulationController. Counterpart to main.py's headless CSV runner.
"""

import sys

# Import ppets (and therefore ppets.ui) before any direct PyQt6 import in
# this file — ppets/__init__.py registers PyQt6's own Qt6 DLL directory
# ahead of PATH, working around a DLL conflict with other installed
# software (see that file's docstring). Must stay first.
from ppets.ui import MainWindow

from PyQt6.QtWidgets import QApplication


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
Shared pytest fixtures. A single session-scoped QApplication is needed
before any QObject (SimulationController, its QTimer, or any widget)
can be constructed — Qt requires one live application instance per
process, not per test.
"""

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app

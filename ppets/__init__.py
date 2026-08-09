"""
On Windows, some unrelated installed software (observed: MiKTeX) ships
its own Qt6Core.dll on PATH. If it's found before PyQt6's own bundled
Qt6 DLLs, importing PyQt6.QtWidgets fails with:
    ImportError: DLL load failed while importing QtWidgets:
    The specified procedure could not be found.
because the two Qt6 builds' DLLs are ABI-mismatched. Registering
PyQt6's own Qt6/bin directory via os.add_dll_directory() makes Windows
prefer it over PATH, without touching PATH or any other software.
Must run before anything imports PyQt6.QtCore/QtWidgets/etc. — since
this is the package `__init__`, that's guaranteed for any `ppets.*`
import (e.g. `ppets.ui`).
"""

import os
import sys

if sys.platform == "win32":
    try:
        import PyQt6
    except ImportError:
        pass
    else:
        _qt_bin_dir = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "bin")
        if os.path.isdir(_qt_bin_dir):
            os.add_dll_directory(_qt_bin_dir)

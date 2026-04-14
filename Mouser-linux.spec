# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for building a portable Linux distribution.

Run:
    python3 -m PyInstaller Mouser-linux.spec --noconfirm

Output: dist/Mouser/  (directory with Mouser executable + dependencies)
"""

import os
import shutil

ROOT = os.path.abspath(".")

a = Analysis(
    ["main_qml.py"],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "ui", "qml"), os.path.join("ui", "qml")),
        (os.path.join(ROOT, "images"), "images"),
    ],
    hiddenimports=[
        "hid",
        "logging.handlers",
        "evdev",
        "ui.locale_manager",
        "PySide6.QtQuick",
        "PySide6.QtQuickControls2",
        "PySide6.QtQml",
        "PySide6.QtNetwork",
        "PySide6.QtOpenGL",
        "PySide6.QtSvg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim PySide6 modules the app does not import at runtime.
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtLocation",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSerialBus",
        "PySide6.QtTest",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSql",
        "PySide6.QtTextToSpeech",
        "PySide6.QtQuick3D",
        "PySide6.QtVirtualKeyboard",
        "PySide6.QtGraphs",
        "PySide6.Qt5Compat",
        # Designer / tooling modules are not needed in the packaged app.
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtUiTools",
        "PySide6.QtXml",
        "PySide6.QtConcurrent",
        "PySide6.QtStateMachine",
        "PySide6.QtHttpServer",
        "PySide6.QtSpatialAudio",
        # Trim large unused stdlib bundles.
        "unittest",
        "xmlrpc",
        "pydoc",
        "doctest",
        "tkinter",
        "test",
        "distutils",
        "setuptools",
        "ensurepip",
        "lib2to3",
        "idlelib",
        "turtledemo",
        "turtle",
        "sqlite3",
        "multiprocessing",
    ],
    noarchive=False,
)

# Filter Qt shared libs and optional QML/plugin families that PyInstaller hooks
# often pull in even though Mouser never loads them.
UNWANTED_PATTERNS = [
    "QtWebEngine",
    "QtWebChannel",
    "QtWebSockets",
    "Qt3D",
    "QtMultimedia",
    "QtMultimediaWidgets",
    "QtBluetooth",
    "QtLocation",
    "QtPositioning",
    "QtSensors",
    "QtSerialPort",
    "QtPdf",
    "QtCharts",
    "QtDataVisualization",
    "QtRemoteObjects",
    "QtTextToSpeech",
    "QtQuick3D",
    "QtVirtualKeyboard",
    "QtGraphs",
    "Qt5Compat",
    "QtWebView",
    "QtTest",
    "QtLabsAnimation",
    "QtLabsFolderListModel",
    "QtLabsPlatform",
    "QtLabsQmlModels",
    "QtLabsSettings",
    "QtLabsSharedImage",
    "QtLabsWavefrontMesh",
    "QtQuickTest",
    "QtScxml",
    "QtScxmlQml",
    "QtSpatialAudio",
    "QtSql",
]

# Keep the Material + Basic control stacks and drop the unused optional styles.
UNUSED_QUICK_CONTROLS_PATTERNS = [
    "QtQuickControls2Fusion",
    "QtQuickControls2FusionStyleImpl",
    "QtQuickControls2Imagine",
    "QtQuickControls2ImagineStyleImpl",
    "QtQuickControls2Universal",
    "QtQuickControls2UniversalStyleImpl",
    "QtQuickControls2FluentWinUI3StyleImpl",
    "QtQuickControls2IOSStyleImpl",
    "QtQuickControls2MacOSStyleImpl",
]

UNUSED_QUICK_CONTROLS_QML_DIRS = [
    "/qtquick/controls/fusion/",
    "/qtquick/controls/fluentwinui3/",
    "/qtquick/controls/imagine/",
    "/qtquick/controls/universal/",
    "/qtquick/controls/ios/",
    "/qtquick/controls/macos/",
]


def is_unwanted(path_or_toc_entry):
    src = ""
    if isinstance(path_or_toc_entry, (list, tuple)) and len(path_or_toc_entry) >= 1:
        src = path_or_toc_entry[0] or ""
    elif isinstance(path_or_toc_entry, str):
        src = path_or_toc_entry
    src_lower = src.lower()
    for pat in UNWANTED_PATTERNS:
        if pat.lower() in src_lower:
            return True
    for pat in UNUSED_QUICK_CONTROLS_PATTERNS:
        if pat.lower() in src_lower:
            return True
    for qml_dir in UNUSED_QUICK_CONTROLS_QML_DIRS:
        if qml_dir in src_lower:
            return True
    if "/plugins/" in src_lower:
        for pat in ("webengine", "multimedia", "printsupport", "qmltooling", "sensorgestures"):
            if pat in src_lower:
                return True
    return False


a.binaries = [b for b in a.binaries if not is_unwanted(b)]
a.datas = [d for d in a.datas if not is_unwanted(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Mouser",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Mouser",
)

# PyInstaller can still pull transitive Qt payload into the collected dist
# even after Analysis-time filtering, so trim the packaged tree directly.
DIST_QT = os.path.join("dist", "Mouser", "_internal", "PySide6", "Qt")
KEEP_QML = {"QtCore", "QtQml", "QtQuick", "QtNetwork"}
KEEP_QTQUICK = {"Controls", "Layouts", "Templates", "Window"}
UNWANTED_PLUGIN_DIRS = {"webengine", "multimedia", "printsupport", "qmltooling", "sensorgestures"}
UNWANTED_FILENAMES = {"libqpdf.so"}


def cleanup_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        print(f"  [cleanup] removed {path}")
        return
    if os.path.exists(path):
        os.remove(path)
        print(f"  [cleanup] removed {path}")


def cleanup_qt_dist():
    if not os.path.isdir(DIST_QT):
        return

    lib_root = os.path.join(DIST_QT, "lib")
    if os.path.isdir(lib_root):
        for name in os.listdir(lib_root):
            full_path = os.path.join(lib_root, name)
            if name in UNWANTED_FILENAMES or is_unwanted(full_path):
                cleanup_path(full_path)

    qml_root = os.path.join(DIST_QT, "qml")
    if os.path.isdir(qml_root):
        for name in os.listdir(qml_root):
            full_path = os.path.join(qml_root, name)
            if name not in KEEP_QML:
                cleanup_path(full_path)

        qtquick_root = os.path.join(qml_root, "QtQuick")
        if os.path.isdir(qtquick_root):
            for name in os.listdir(qtquick_root):
                full_path = os.path.join(qtquick_root, name)
                if name not in KEEP_QTQUICK:
                    cleanup_path(full_path)

        for current_root, dirnames, filenames in os.walk(qml_root, topdown=False):
            for filename in filenames:
                full_path = os.path.join(current_root, filename)
                if is_unwanted(full_path):
                    cleanup_path(full_path)
            for dirname in dirnames:
                full_path = os.path.join(current_root, dirname)
                if is_unwanted(full_path):
                    cleanup_path(full_path)

    plugins_root = os.path.join(DIST_QT, "plugins")
    if os.path.isdir(plugins_root):
        for name in os.listdir(plugins_root):
            full_path = os.path.join(plugins_root, name)
            if name in UNWANTED_PLUGIN_DIRS or is_unwanted(full_path):
                cleanup_path(full_path)
            elif os.path.isdir(full_path):
                for child_name in os.listdir(full_path):
                    child_path = os.path.join(full_path, child_name)
                    if child_name in UNWANTED_FILENAMES or is_unwanted(child_path):
                        cleanup_path(child_path)

    cleanup_path(os.path.join(DIST_QT, "translations"))


print("[Mouser] Post-build Linux Qt cleanup...")
cleanup_qt_dist()
print("[Mouser] Linux Qt cleanup done.")

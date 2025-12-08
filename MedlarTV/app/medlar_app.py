import sys
import os
os.environ.setdefault("QT_QPA_PLATFORM", "windows")
try:
    if hasattr(sys, "_MEIPASS"):
        candidates = [
            os.path.join(sys._MEIPASS, "_internal", "PySide6", "plugins"),
            os.path.join(sys._MEIPASS, "PySide6", "plugins"),
        ]
        for p in candidates:
            if os.path.isdir(p):
                os.environ["QT_PLUGIN_PATH"] = p
                break
except Exception:
    pass
import time
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QCheckBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from dotenv import load_dotenv
import subprocess
import signal
import yaml

# Ensure package import works in both source and frozen modes
try:
    import MedlarTV  # noqa: F401
except Exception:
    candidates = [
        Path.cwd(),
        Path(sys.executable).resolve().parent.parent,
        Path(__file__).resolve().parents[2],
        Path(os.path.expanduser("~")) / "medlartv",
        Path("C:/Users/znorr/medlartv"),
    ]
    for base in candidates:
        if (base / "MedlarTV").exists():
            sys.path.insert(0, str(base))
            break

# Defer MedlarTV imports to runtime to avoid startup failures in packaged mode


class ControlCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            load_dotenv()
        except Exception:
            pass
        self.setWindowTitle("Medlar Control Center")
        self.setMinimumSize(520, 360)

        try:
            icon_path_env = os.getenv("APP_ICON_PATH", "").strip()
            icon_candidates = []
            if icon_path_env:
                icon_candidates.append(Path(icon_path_env))
            bases = [
                Path(__file__).resolve().parent,
                Path(__file__).resolve().parents[1] / "app",
                Path.cwd() / "MedlarTV" / "app",
                Path.cwd(),
                Path("C:/Users/znorr/medlartv"),
            ]
            for b in bases:
                icon_candidates.extend([
                    b / "medlar.ico",
                ])
            for p in icon_candidates:
                try:
                    if p.exists():
                        self.setWindowIcon(QIcon(str(p)))
                        break
                except Exception:
                    pass
        except Exception:
            pass

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignLeft)

        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_restart = QPushButton("Restart")

        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_restart.clicked.connect(self.on_restart)

        self.chk_llm = QCheckBox("LLM Brain")
        self.chk_pcg = QCheckBox("Pokémon Auto-Catch")
        self.chk_filter = QCheckBox("Content Filter")
        self.chk_timers = QCheckBox("Timers")
        self.chk_fuzzy = QCheckBox("Fuzzy Trigger")

        try:
            for c in (self.chk_llm, self.chk_pcg, self.chk_filter, self.chk_timers, self.chk_fuzzy):
                c.setTristate(False)
        except Exception:
            pass

        self.chk_llm.clicked.connect(lambda checked: self.update_toggle("llm_brain", checked))
        self.chk_pcg.clicked.connect(lambda checked: self.update_toggle("pcg_auto_catch", checked))
        self.chk_filter.clicked.connect(lambda checked: self.update_toggle("content_filter", checked))
        self.chk_timers.clicked.connect(lambda checked: self.update_toggle("timers", checked))
        self.chk_fuzzy.clicked.connect(lambda checked: self.update_toggle("fuzzy_trigger", checked))

        row = QHBoxLayout()
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_stop)
        row.addWidget(self.btn_restart)

        toggles = QVBoxLayout()
        toggles.addWidget(self.chk_llm)
        toggles.addWidget(self.chk_pcg)
        toggles.addWidget(self.chk_filter)
        toggles.addWidget(self.chk_timers)
        toggles.addWidget(self.chk_fuzzy)

        layout = QVBoxLayout()
        layout.addLayout(row)
        layout.addWidget(self.status_label)
        layout.addLayout(toggles)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        try:
            bases = [
                Path(sys.executable).resolve().parents[3] if hasattr(sys, "_MEIPASS") or sys.executable else Path.cwd(),
                Path(__file__).resolve().parents[2],
                Path.cwd(),
                Path(os.path.expanduser("~")) / "medlartv",
                Path("C:/Users/znorr/medlartv"),
            ]
            root = None
            for b in bases:
                try:
                    if (b / "MedlarTV" / "config").exists():
                        root = b
                        break
                except Exception:
                    pass
            if root:
                os.environ["MEDLARTV_ROOT"] = str(root)
        except Exception:
            pass

        try:
            self.refresh_settings()
        except Exception:
            pass

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(2000)

        try:
            app = QApplication.instance()
            if app:
                app.aboutToQuit.connect(self._kill_all_medlar)
        except Exception:
            pass

    def refresh_settings(self):
        s = self._load_settings()
        try:
            self.chk_llm.blockSignals(True)
            self.chk_pcg.blockSignals(True)
            self.chk_filter.blockSignals(True)
            self.chk_timers.blockSignals(True)
            self.chk_fuzzy.blockSignals(True)
        except Exception:
            pass
        try:
            self.chk_llm.setChecked(bool(s.get("llm_brain", True)))
            self.chk_pcg.setChecked(bool(s.get("pcg_auto_catch", True)))
            self.chk_filter.setChecked(bool(s.get("content_filter", True)))
            self.chk_timers.setChecked(bool(s.get("timers", True)))
            self.chk_fuzzy.setChecked(bool(s.get("fuzzy_trigger", True)))
        except Exception:
            pass
        try:
            self.chk_llm.blockSignals(False)
            self.chk_pcg.blockSignals(False)
            self.chk_filter.blockSignals(False)
            self.chk_timers.blockSignals(False)
            self.chk_fuzzy.blockSignals(False)
        except Exception:
            pass

    def update_toggle(self, key: str, value: bool):
        sp = self._settings_path()
        cur = self._load_settings()
        cur[key] = bool(value)
        self._save_settings(cur)
        try:
            logs_dir = Path.cwd() / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            with (logs_dir / "control_center.log").open("a", encoding="utf-8") as f:
                f.write(f"toggle {key} -> {value} path={str(sp)}\n")
        except Exception:
            pass
        try:
            self.refresh_settings()
        except Exception:
            pass

    def _settings_path(self) -> Path:
        base = None
        try:
            env_root = os.getenv("MEDLARTV_ROOT", "").strip()
            if env_root:
                b = Path(env_root)
                if (b / "MedlarTV" / "config").exists():
                    base = b
        except Exception:
            pass
        if base is None:
            for b in [Path("C:/Users/znorr/medlartv"), Path(os.path.expanduser("~")) / "medlartv", Path.cwd()]:
                try:
                    if (b / "MedlarTV" / "config").exists():
                        base = b
                        break
                except Exception:
                    pass
        if base is None:
            base = Path("C:/Users/znorr/medlartv")
        p = base / "MedlarTV" / "config" / "app_settings.yaml"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return p

    def _load_settings(self) -> dict:
        p = self._settings_path()
        d = {
            "llm_brain": True,
            "pcg_auto_catch": True,
            "ignore_viewer_pokecatch": True,
            "content_filter": True,
            "timers": True,
            "fuzzy_trigger": True,
        }
        try:
            if p.exists():
                with p.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    d.update({k: bool(v) for k, v in data.items() if k in d})
        except Exception:
            pass
        return d

    def _save_settings(self, data: dict) -> None:
        p = self._settings_path()
        try:
            with p.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        except Exception:
            pass

    def refresh_status(self):
        irc = False
        ollama = False
        twitch_ok = False
        bases = [
            Path(sys.executable).resolve().parents[3] if hasattr(sys, "_MEIPASS") or sys.executable else Path.cwd(),
            Path(__file__).resolve().parents[2],
            Path.cwd(),
            Path("C:/Users/znorr/medlartv"),
        ]
        roots = []
        for b in bases:
            try:
                if (b / "logs").exists():
                    roots.append(b)
            except Exception:
                pass
        if not roots:
            roots = [Path.cwd()]
        for root in roots:
            try:
                tl = root / "logs" / "twitch_listener_log.txt"
                if tl.exists():
                    txt = tl.read_text(encoding="utf-8", errors="ignore")
                    tail = txt[-8000:]
                    if ("[IRC] Connected" in tail) or ("Twitch listener started" in tail):
                        irc = True
                if not irc:
                    mc = root / "logs" / "medlar_core.log"
                    if mc.exists():
                        txt = mc.read_text(encoding="utf-8", errors="ignore")
                        tail = txt[-12000:]
                        if ("[IRC] Connected" in tail) or ("[Listener] Twitch listener started" in tail):
                            irc = True
            except Exception:
                pass
            try:
                oslog = root / "logs" / "ollama_server.log"
                if oslog.exists():
                    txt = oslog.read_text(encoding="utf-8", errors="ignore")
                    tail = txt[-8000:]
                    if (
                        "bind: Only one usage" in tail
                        or "/api/tags" in tail
                        or "/api/chat" in tail
                        or "Listening on 127.0.0.1:11434" in tail
                    ):
                        ollama = True
                if not ollama:
                    lb = root / "logs" / "llm_brain.txt"
                    if lb.exists():
                        txt = lb.read_text(encoding="utf-8", errors="ignore")
                        tail = txt[-4000:]
                        if "Ollama" in tail and ("health" in tail or "ready" in tail or "connected" in tail):
                            ollama = True
            except Exception:
                pass
            try:
                sm = root / "logs" / "stream_management.txt"
                if sm.exists():
                    txt = sm.read_text(encoding="utf-8", errors="ignore")
                    tail = txt[-6000:]
                    if "✅ Twitch tokens verified" in tail or "verify_twitch_tokens() -> True" in tail:
                        twitch_ok = True
            except Exception:
                pass
        self.status_label.setText(f"Status: IRC={'OK' if irc else 'OFF'} | Ollama={'OK' if ollama else 'OFF'} | Twitch={'OK' if twitch_ok else 'FAIL'}")

    def on_start(self):
        try:
            base_candidates = [
                Path(sys.executable).resolve().parents[3] if hasattr(sys, "_MEIPASS") or sys.executable else Path.cwd(),
                Path(__file__).resolve().parents[2],
                Path.cwd(),
                Path(os.path.expanduser("~")) / "medlartv",
                Path("C:/Users/znorr/medlartv"),
            ]
            root = None
            for c in base_candidates:
                try:
                    if (c / "launcher.py").exists() and (c / ".venv").exists():
                        root = c
                        break
                except Exception:
                    pass
            if root is None:
                root = Path.cwd()

            vpy = root / ".venv" / "Scripts" / "python.exe"
            py = vpy if vpy.exists() else Path(os.getenv("PYTHON", ""))
            if not py or (isinstance(py, Path) and not py.exists()):
                common = Path("C:/Users/znorr/AppData/Local/Programs/Python/Python311/python.exe")
                py = common if common.exists() else vpy

            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            logs_dir = Path.cwd() / "logs"
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            spawn_log = None
            try:
                spawn_log = (logs_dir / "launcher_spawn.log").open("a", encoding="utf-8")
                with (logs_dir / "control_center.log").open("a", encoding="utf-8") as f:
                    f.write(f"start cmd: {py} {root / 'launcher.py'}\n")
            except Exception:
                spawn_log = None
            args = [str(py), str(root / "launcher.py")]
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            self.launcher_proc = subprocess.Popen(
                args,
                cwd=str(root),
                env=env,
                shell=False,
                stdout=spawn_log if spawn_log else subprocess.DEVNULL,
                stderr=spawn_log if spawn_log else subprocess.DEVNULL,
                creationflags=flags,
            )
            QTimer.singleShot(800, self._post_start_check)
            self.status_label.setText("Status: Starting...")
        except Exception:
            pass

    def _post_start_check(self):
        try:
            if hasattr(self, "launcher_proc") and self.launcher_proc:
                rc = self.launcher_proc.poll()
                if rc is not None:
                    try:
                        logs_dir = Path.cwd() / "logs"
                        with (logs_dir / "control_center.log").open("a", encoding="utf-8") as f:
                            f.write(f"start failed rc={rc}\n")
                    except Exception:
                        pass
                    self.status_label.setText("Status: Idle")
        except Exception:
            pass

    def _force_cleanup(self):
        try:
            if os.name == "nt":
                script = "$ErrorActionPreference='SilentlyContinue';" \
                    "foreach($p in 11434,8000,8765){Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | % {taskkill /PID $($_.OwningProcess) /F | Out-Null}};" \
                    "Get-CimInstance Win32_Process | Where-Object {($_.CommandLine -match 'MedlarTV') -or ($_.CommandLine -match 'launcher\\.py')} | % {taskkill /PID $($_.ProcessId) /F | Out-Null};" \
                    "Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '" + str((Path.cwd()/".venv"/"Scripts"/"python.exe")).replace("\\","\\\\") + "' } | % { taskkill /PID $_.Id /F | Out-Null }"
                try:
                    subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command", script], cwd=str(Path.cwd()), creationflags=(subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0))
                except Exception:
                    pass
        except Exception:
            pass

    def _kill_all_medlar(self):
        try:
            if os.name == "nt":
                script = "$ErrorActionPreference='SilentlyContinue';" \
                    "$pidSelf=" + str(os.getpid()) + ";" \
                    "$patterns=@('launcher\\.py','MedlarTV','libretranslate\\.main','ollama serve');" \
                    "$p=Get-CimInstance Win32_Process | Where-Object { $n=$_.Name; $c=$_.CommandLine; if ($_.ProcessId -eq $pidSelf) { return $false }; foreach($pat in $patterns){ if(($c -match $pat) -or ($n -match $pat)){ return $true } }; return $false };" \
                    "$p | % { taskkill /PID $($_.ProcessId) /T /F | Out-Null };" \
                    "Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '" + str((Path.cwd()/".venv"/"Scripts"/"python.exe")).replace("\\","\\\\") + "' } | % { if ($_.Id -ne $pidSelf) { taskkill /PID $_.Id /T /F | Out-Null } };" \
                    "foreach($port in 11434,8000,8765){ Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | % { taskkill /PID $($_.OwningProcess) /T /F | Out-Null } }"
                try:
                    subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command", script], cwd=str(Path.cwd()), creationflags=(subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0))
                except Exception:
                    pass
        except Exception:
            pass

    def on_stop(self):
        try:
            if hasattr(self, "launcher_proc") and self.launcher_proc:
                try:
                    if os.name == "nt":
                        try:
                            pid = self.launcher_proc.pid
                            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], creationflags=(subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0))
                        except Exception:
                            try:
                                self.launcher_proc.terminate()
                            except Exception:
                                pass
                    else:
                        self.launcher_proc.terminate()
                except Exception:
                    pass
                try:
                    for _ in range(6):
                        rc = self.launcher_proc.poll()
                        if rc is not None:
                            break
                        time.sleep(0.25)
                except Exception:
                    pass
                try:
                    if self.launcher_proc and self.launcher_proc.poll() is None:
                        self._force_cleanup()
                except Exception:
                    pass
                try:
                    self.launcher_proc = None
                except Exception:
                    pass
            try:
                self._kill_all_medlar()
            except Exception:
                pass
            self.status_label.setText("Status: Idle")
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self._kill_all_medlar()
        except Exception:
            pass
        try:
            super().closeEvent(event)
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception:
            pass

    def on_restart(self):
        self.on_stop()
        time.sleep(0.5)
        self.on_start()


def main():
    # simple file logging to help diagnose startup issues
    _log_file = None
    try:
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _log_file = logs_dir / "control_center.log"
        with _log_file.open("a", encoding="utf-8") as f:
            f.write("launching app\n")
    except Exception:
        pass

    try:
        app = QApplication(sys.argv)
    except Exception as e:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Failed to create QApplication: {e}", "Medlar Control Center", 0)
        except Exception:
            pass
        return
    try:
        app.setQuitOnLastWindowClosed(True)
    except Exception:
        pass

    try:
        w = ControlCenter()
    except Exception as e:
        try:
            if _log_file:
                with _log_file.open("a", encoding="utf-8") as f:
                    f.write(f"control center init failed: {e}\n")
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Control Center failed: {e}", "Medlar Control Center", 0)
        except Exception:
            pass
        return
    try:
        w.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    except Exception:
        pass
    w.show()
    try:
        if _log_file:
            with _log_file.open("a", encoding="utf-8") as f:
                f.write("window shown\n")
    except Exception:
        pass
    try:
        w.raise_(); w.activateWindow()
    except Exception:
        pass
    try:
        t = QTimer()
        t.setSingleShot(True)
        def _bring():
            try:
                w.showNormal(); w.raise_(); w.activateWindow()
            except Exception:
                pass
        t.timeout.connect(_bring)
        t.start(250)
    except Exception:
        pass
    try:
        if _log_file:
            with _log_file.open("a", encoding="utf-8") as f:
                f.write("entering event loop\n")
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

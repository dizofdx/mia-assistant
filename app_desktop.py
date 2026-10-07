# app_desktop.py — Нативное десктопное приложение Мии (вместо браузера)
import os, sys, time, subprocess, urllib.request

def ensure_server():
    """Проверяет, запущен ли бэкенд Мии на порту 8000. Если нет — запускает."""
    for _ in range(3):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

    # Запускаем main.py в фоне
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        py_candidates = [
            os.path.expandvars(r"%LocalAppData%\Python\pythoncore-3.14-64\pythonw.exe"),
            os.path.expandvars(r"%LocalAppData%\Python\pythoncore-3.14-64\python.exe"),
            "pythonw",
            "python",
        ]
        py_exe = "pythonw"
        for cand in py_candidates:
            if os.path.isabs(cand) and os.path.exists(cand):
                py_exe = cand
                break
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        py_exe = sys.executable

    main_py = os.path.join(base_dir, "main.py")

    # Флаги окружения для Intel MKL и бесконсольного режима
    env = os.environ.copy()
    env["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | 0x00000200 # DETACHED_PROCESS

    subprocess.Popen([py_exe, main_py], cwd=base_dir, env=env, creationflags=creationflags)

    # Ждем готовности сервера (до 15 сек для Whisper)
    for _ in range(30):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    return False

def launch_native_window():
    """Запускает чистое нативное окно приложения без адресной строки и вкладок."""
    url = "http://127.0.0.1:8000"

    # 1. Попытка через нативный режим Edge App (максимально быстрый WebGL, нулевой оверхед, нативное окно Windows)
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for ep in edge_paths:
        if os.path.exists(ep):
            cmd = [
                ep,
                f"--app={url}",
                "--window-size=1260,840",
                "--app-id=mia_assistant_ai"
            ]
            try:
                proc = subprocess.Popen(cmd)
                proc.wait()
                return
            except Exception:
                pass

    # 2. Попытка через pywebview
    try:
        import webview
        win = webview.create_window(
            title="Мия • AI Ассистент",
            url=url,
            width=1260,
            height=840,
            resizable=True,
            text_select=True,
            zoomable=True
        )
        webview.start()
        return
    except Exception as e:
        print(f"pywebview failed: {e}")

    # 3. Fallback: системный браузер
    import webbrowser
    webbrowser.open(url)

if __name__ == "__main__":
    ensure_server()
    launch_native_window()

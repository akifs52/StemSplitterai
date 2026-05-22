import os
import shutil
import subprocess
import sys


def _app_dirs():
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))
        dirs.append(getattr(sys, "_MEIPASS", ""))
    dirs.append(os.getcwd())
    dirs.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    result = []
    for d in dirs:
        if d and d not in result:
            result.append(d)
    return result


def resolve_program(name):
    candidates = []
    exe_name = name if os.path.splitext(name)[1] else name + (".exe" if os.name == "nt" else "")
    for base in _app_dirs():
        candidates.append(os.path.join(base, exe_name))
        candidates.append(os.path.join(base, "bin", exe_name))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return shutil.which(name) or name


def ffmpeg_program():
    return resolve_program("ffmpeg")


def no_window_kwargs():
    if os.name != "nt":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}


def run_hidden(args, **kwargs):
    kwargs.update(no_window_kwargs())
    return subprocess.run(args, **kwargs)


def popen_hidden(args, **kwargs):
    kwargs.update(no_window_kwargs())
    return subprocess.Popen(args, **kwargs)

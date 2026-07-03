"""Project Launcher — Entry point.

A lightweight Windows desktop tool for quickly browsing and launching
your development projects from a central directory.

Usage:
    python main.py            # Run directly
    ProjectLauncher.exe        # Run the built executable
"""

import sys
import os

from app_paths import get_log_path

# Redirect stderr on frozen builds (no console window)
if getattr(sys, 'frozen', False):
    try:
        sys.stderr = open(get_log_path('error.log'), 'a', encoding='utf-8')
    except OSError:
        pass


def main():
    from app import App
    try:
        app = App()
        app.run()
    except Exception as e:
        # Last-resort error logging
        try:
            with open(
                get_log_path('crash.log'),
                'a', encoding='utf-8',
            ) as crash_log:
                import traceback, datetime
                crash_log.write(f'\n[{datetime.datetime.now().isoformat()}] CRASH:\n')
                traceback.print_exc(file=crash_log)
        except Exception:
            pass
        # Try to show in a message box
        try:
            from tkinter import messagebox
            messagebox.showerror(
                '项目启动器 — 错误',
                f'发生了意外错误:\n\n{e}\n\n'
                f'详细日志请查看 %TEMP%\\ProjectLauncher\\error.log',
            )
        except Exception:
            pass
        raise


if __name__ == '__main__':
    # Ensure the current directory is the script/exe directory
    # so relative paths work correctly
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    main()

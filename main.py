from __future__ import annotations

import sys

from route_manager.admin import is_admin, is_windows, relaunch_as_admin, show_native_error


def main() -> int:
    if not is_windows():
        print("RoutePilot 仅支持 Windows 10 / 11。", file=sys.stderr)
        return 1

    no_elevate = "--no-elevate" in sys.argv
    if not is_admin() and not no_elevate:
        if relaunch_as_admin():
            return 0
        show_native_error("RoutePilot 需要管理员权限才能管理系统路由。")
        return 1

    from route_manager.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())


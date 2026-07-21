from __future__ import annotations

import base64
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any


class PowerShellError(RuntimeError):
    pass


@dataclass(slots=True)
class PowerShellRunner:
    timeout: int = 35

    def execute(self, script: str) -> str:
        wrapped = (
            "$ErrorActionPreference='Stop';"
            "$ProgressPreference='SilentlyContinue';"
            "[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false);"
            "Import-Module NetTCPIP -ErrorAction Stop;"
            "try {"
            f"{script}"
            "} catch {"
            "[Console]::Error.WriteLine($_.Exception.Message);"
            "exit 1"
            "}"
        )
        encoded = base64.b64encode(wrapped.encode("utf-16-le")).decode("ascii")
        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-EncodedCommand",
                    encoded,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                startupinfo=startupinfo,
                creationflags=creationflags,
                check=False,
            )
        except FileNotFoundError as exc:
            raise PowerShellError("未找到 Windows PowerShell，无法读取系统路由。") from exc
        except subprocess.TimeoutExpired as exc:
            raise PowerShellError("Windows 网络配置响应超时，请稍后重试。") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if not detail:
                detail = f"PowerShell 退出代码：{result.returncode}"
            raise PowerShellError(detail)
        return result.stdout.strip()

    def execute_json(self, script: str) -> Any:
        output = self.execute(script)
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise PowerShellError("Windows 返回了无法识别的网络配置数据。") from exc


def ps_quote(value: str) -> str:
    """Quote a previously validated string as a PowerShell literal."""
    return "'" + value.replace("'", "''") + "'"

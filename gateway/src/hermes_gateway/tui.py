from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from .config import Settings
from .security import now_utc, parse_utc
from .store import SQLiteStore


@dataclass
class TuiRuntimeSession:
    session_id: str
    process: asyncio.subprocess.Process
    master_fd: int
    output: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    reader_task: asyncio.Task[None] | None = None


class LocalPtyManager:
    """Development-only PTY bridge guarded by gateway policy."""

    def __init__(self, *, store: SQLiteStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings
        self._sessions: dict[str, TuiRuntimeSession] = {}
        self._lock = asyncio.Lock()

    async def create_runtime(
        self,
        *,
        session_id: str,
        command: str,
        working_directory: str,
    ) -> None:
        self._ensure_posix()
        async with self._lock:
            if session_id in self._sessions:
                return
            master_fd, slave_fd = _open_pty()
            try:
                process = await asyncio.create_subprocess_exec(
                    command,
                    cwd=working_directory,
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    preexec_fn=os.setsid,
                )
            except BaseException:
                os.close(master_fd)
                os.close(slave_fd)
                raise
            os.close(slave_fd)
            runtime = TuiRuntimeSession(
                session_id=session_id,
                process=process,
                master_fd=master_fd,
            )
            runtime.reader_task = asyncio.create_task(self._read_output(runtime))
            self._sessions[session_id] = runtime

    async def attach(self, session_id: str) -> None:
        runtime = self._sessions.get(session_id)
        if runtime is None or runtime.process.returncode is not None:
            raise HTTPException(status.HTTP_410_GONE, "TUI runtime is not available")
        self._store.update_tui_session_state(session_id, "active")

    async def detach(self, session_id: str) -> None:
        self._store.update_tui_session_state(session_id, "detached")

    async def close(self, session_id: str) -> None:
        runtime = self._sessions.pop(session_id, None)
        if runtime is not None:
            await self._terminate(runtime)
            if runtime.reader_task is not None and not runtime.reader_task.done():
                runtime.reader_task.cancel()
                try:
                    await asyncio.wait_for(runtime.reader_task, timeout=0.2)
                except (TimeoutError, asyncio.CancelledError):
                    pass
        self._store.update_tui_session_state(session_id, "closed")

    async def close_all(self) -> None:
        for session_id in list(self._sessions):
            await self.close(session_id)

    async def write(self, session_id: str, text: str) -> None:
        runtime = self._runtime(session_id)
        if not text:
            return
        await asyncio.to_thread(os.write, runtime.master_fd, text.encode("utf-8"))
        self._store.touch_tui_session(session_id)

    async def resize(self, session_id: str, *, rows: int, cols: int) -> None:
        runtime = self._runtime(session_id)
        if rows < 1 or cols < 1:
            return
        await asyncio.to_thread(_resize_pty, runtime.master_fd, rows, cols)
        self._store.touch_tui_session(session_id)

    async def next_output(self, session_id: str, timeout: float = 0.1) -> str | None:
        runtime = self._runtime(session_id)
        try:
            return await asyncio.wait_for(runtime.output.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def cleanup_idle_sessions(self) -> None:
        now = now_utc()
        for session in self._store.list_tui_sessions():
            if session["state"] not in {"active", "detached", "requested"}:
                continue
            last_activity_at = parse_utc(session["last_activity_at"])
            idle_seconds = (now - last_activity_at).total_seconds()
            if idle_seconds < self._settings.tui_idle_timeout_seconds:
                continue
            await self.close(session["session_id"])

    def is_running(self, session_id: str) -> bool:
        runtime = self._sessions.get(session_id)
        return runtime is not None and runtime.process.returncode is None

    async def _read_output(self, runtime: TuiRuntimeSession) -> None:
        try:
            while runtime.process.returncode is None:
                try:
                    data = await asyncio.to_thread(os.read, runtime.master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                await runtime.output.put(data.decode("utf-8", errors="replace"))
        finally:
            await runtime.process.wait()
            self._sessions.pop(runtime.session_id, None)
            try:
                os.close(runtime.master_fd)
            except OSError:
                pass
            try:
                session = self._store.get_tui_session(runtime.session_id)
            except KeyError:
                return
            if session["state"] not in {"closed", "failed"}:
                self._store.update_tui_session_state(runtime.session_id, "closed")

    async def _terminate(self, runtime: TuiRuntimeSession) -> None:
        if runtime.process.returncode is None:
            try:
                os.killpg(runtime.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(runtime.process.wait(), timeout=2)
            except TimeoutError:
                try:
                    os.killpg(runtime.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await runtime.process.wait()
        try:
            os.close(runtime.master_fd)
        except OSError:
            pass

    def _runtime(self, session_id: str) -> TuiRuntimeSession:
        runtime = self._sessions.get(session_id)
        if runtime is None or runtime.process.returncode is not None:
            raise HTTPException(status.HTTP_410_GONE, "TUI runtime is not available")
        return runtime

    def _ensure_posix(self) -> None:
        if os.name != "posix":
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "local PTY requires POSIX")


def validate_tui_request(
    *,
    settings: Settings,
    command: str | None,
    working_directory: str | None,
) -> tuple[str, str]:
    if not settings.tui_enable_local_pty:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "local TUI PTY is disabled")

    selected_command = command or settings.tui_default_command
    allowed_commands = set(settings.tui_allowed_commands)
    if not allowed_commands:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "TUI command allowlist is empty")
    if selected_command not in allowed_commands:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "TUI command is not allowlisted")

    allowed_root = Path(settings.tui_allowed_working_directory).expanduser().resolve()
    requested_workdir = Path(working_directory or allowed_root).expanduser().resolve()
    if not _is_relative_to(requested_workdir, allowed_root):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "TUI working directory is outside the allowed root",
        )
    if not requested_workdir.exists() or not requested_workdir.is_dir():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "TUI working directory invalid")

    return selected_command, str(requested_workdir)


def validate_tui_frame(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("TUI frame must be a JSON object")
    frame_type = raw.get("type")
    if frame_type not in {"input", "resize", "ping", "paste", "detach", "close"}:
        raise ValueError("unsupported TUI frame type")
    return raw


def _open_pty() -> tuple[int, int]:
    import pty

    return pty.openpty()


def _resize_pty(master_fd: int, rows: int, cols: int) -> None:
    import fcntl
    import struct
    import termios

    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

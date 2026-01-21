from __future__ import annotations

import sys
import subprocess
import threading
from collections import deque
from typing import Deque, TextIO


def _drain_stream(
    stream: TextIO,
    *,
    sink: TextIO,
    buf: Deque[str],
) -> None:
    """
    Read a text stream line-by-line, write to sink, and keep a tail buffer.
    """
    try:
        for line in iter(stream.readline, ""):
            sink.write(line)
            sink.flush()
            buf.append(line.rstrip("\n"))
    finally:
        try:
            stream.close()
        except Exception:
            pass


def run_streaming(
    cmd: list[str],
    *,
    cwd,
    env: dict[str, str],
    keep_lines: int = 400,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess, stream stdout/stderr live to the terminal, and return
    a CompletedProcess whose stdout/stderr contain only the last `keep_lines`
    lines (tail buffers).
    """
    p = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        bufsize=1,  # line buffered (best effort)
    )

    out_buf: Deque[str] = deque(maxlen=int(keep_lines))
    err_buf: Deque[str] = deque(maxlen=int(keep_lines))

    assert p.stdout is not None
    assert p.stderr is not None

    t_out = threading.Thread(
        target=_drain_stream,
        kwargs={"stream": p.stdout, "sink": sys.stdout, "buf": out_buf},
    )
    t_err = threading.Thread(
        target=_drain_stream,
        kwargs={"stream": p.stderr, "sink": sys.stderr, "buf": err_buf},
    )

    t_out.daemon = True
    t_err.daemon = True
    t_out.start()
    t_err.start()

    rc = p.wait()

    # Process is finished; drain threads should finish quickly too.
    t_out.join()
    t_err.join()

    stdout_tail = ("\n".join(out_buf) + ("\n" if out_buf else "")).rstrip("\n")
    stderr_tail = ("\n".join(err_buf) + ("\n" if err_buf else "")).rstrip("\n")

    return subprocess.CompletedProcess(cmd, rc, stdout=stdout_tail, stderr=stderr_tail)

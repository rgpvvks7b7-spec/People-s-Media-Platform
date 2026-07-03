#!/usr/bin/env python3
import argparse
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import time
import tty


INITIAL_COMMAND = b"/run git status\r"


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resize_pty(fd):
    if not hasattr(termios, "TIOCGWINSZ") or not hasattr(termios, "TIOCSWINSZ"):
        return
    try:
        import fcntl
        import struct

        size = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
        rows, cols, xpixels, ypixels = struct.unpack("HHHH", size)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, xpixels, ypixels))
    except OSError:
        return


def run_aider(model):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("aid7/aid14 must be run from an interactive terminal.", file=sys.stderr)
        return 2

    master_fd, slave_fd = pty.openpty()
    resize_pty(master_fd)

    process = subprocess.Popen(
        ["aider", "--model", model],
        cwd=repo_root(),
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    old_settings = termios.tcgetattr(sys.stdin.fileno())
    command_sent = False
    send_after = time.monotonic() + 1.0

    def handle_resize(signum, frame):
        resize_pty(master_fd)

    old_winch = signal.signal(signal.SIGWINCH, handle_resize)

    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            if process.poll() is not None:
                break

            timeout = 0.05
            readable, _, _ = select.select([master_fd, sys.stdin.fileno()], [], [], timeout)

            if not command_sent and time.monotonic() >= send_after:
                os.write(master_fd, INITIAL_COMMAND)
                command_sent = True

            if master_fd in readable:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)

            if sys.stdin.fileno() in readable:
                data = os.read(sys.stdin.fileno(), 4096)
                if not data:
                    break
                os.write(master_fd, data)
    finally:
        signal.signal(signal.SIGWINCH, old_winch)
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
        try:
            os.close(master_fd)
        except OSError:
            pass

    return process.wait()


def main():
    parser = argparse.ArgumentParser(description="Open Aider and run git status first.")
    parser.add_argument("model", help="Aider model name, for example ollama/qwen2.5-coder:14b")
    args = parser.parse_args()
    return run_aider(args.model)


if __name__ == "__main__":
    raise SystemExit(main())

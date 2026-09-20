# /// script
# dependencies = []
# ///
"""One-command Zephyr coredump analyzer.

Takes an Intel HEX file read from the device via nrfutil and prints the
crash registers and full backtrace.

Usage (run from the project root, inside the NCS toolchain environment):
    python analyze_dump.py <coredump.hex> <zephyr.elf>

Pipeline: ihex -> bin -> strip the 16-byte flash header -> launch
coredump_gdbserver -> gdb batch (registers + bt) -> cleanup.
"""

import os
import subprocess
import sys
import tempfile
import time

GDB = "arm-zephyr-eabi-gdb"
OBJCOPY = "arm-zephyr-eabi-objcopy"
FLASH_HDR_SIZE = 16
GDBSERVER_PORT = 1234


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(f"usage: python {os.path.basename(__file__)} <coredump.hex> <zephyr.elf>")

    hex_file, elf_file = sys.argv[1], sys.argv[2]

    zephyr_base = os.environ.get("ZEPHYR_BASE")
    if not zephyr_base:
        sys.exit("ZEPHYR_BASE is not set; run inside the NCS toolchain environment")

    gdbserver = os.path.join(zephyr_base, "scripts", "coredump", "coredump_gdbserver.py")
    for f in (hex_file, elf_file, gdbserver):
        if not os.path.isfile(f):
            sys.exit(f"file not found: {f}")

    tmpdir = tempfile.mkdtemp(prefix="coredump_")
    raw_bin = os.path.join(tmpdir, "raw.bin")
    dump_bin = os.path.join(tmpdir, "coredump.bin")

    # Intel HEX -> binary
    subprocess.run([OBJCOPY, "-I", "ihex", "-O", "binary", hex_file, raw_bin],
                   check=True)

    # Strip the flash header (32-bit little-endian dump size at offset 4)
    with open(raw_bin, "rb") as f:
        raw = f.read()
    if raw[:2] != b"CD":
        sys.exit("flash partition header magic is not 'CD'; no valid coredump")
    size = int.from_bytes(raw[4:8], "little")
    with open(dump_bin, "wb") as f:
        f.write(raw[FLASH_HDR_SIZE:FLASH_HDR_SIZE + size])
    print(f"[*] dump size = {size} bytes")

    # Launch the coredump GDB server
    server = subprocess.Popen([sys.executable, gdbserver, "--port", str(GDBSERVER_PORT),
                               elf_file, dump_bin],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # Wait until ready. NOTE: do not probe the port with a socket — the
        # gdbserver treats the first TCP connection as the GDB session, so a
        # probe would steal it and GDB would see "No stack".
        for _ in range(25):
            if server.poll() is not None:
                sys.exit("coredump_gdbserver failed to start")
            time.sleep(0.2)

        # GDB batch: print registers and backtrace
        out = subprocess.run(
            [GDB, "-batch",
             "-ex", f"target remote localhost:{GDBSERVER_PORT}",
             "-ex", "info registers pc lr sp",
             "-ex", "bt",
             elf_file],
            capture_output=True, text=True, errors="replace")
        # Drop gdbserver noise lines, keep the useful output
        for line in (out.stdout + out.stderr).splitlines():
            if line.strip() and "Remote " not in line:
                print(line)
    finally:
        server.terminate()

    return 0


if __name__ == "__main__":
    sys.exit(main())

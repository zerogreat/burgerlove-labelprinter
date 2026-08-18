import os
import socket

PRINTER_IP = os.getenv("PRINTER_IP", "")
PRINTER_PORT = int(os.getenv("PRINTER_PORT", "9100"))


class PrinterError(Exception):
    pass


def send_to_printer(zpl: str) -> None:
    if not PRINTER_IP:
        raise PrinterError("PRINTER_IP is not configured")
    try:
        with socket.create_connection((PRINTER_IP, PRINTER_PORT), timeout=3) as sock:
            sock.sendall(zpl.encode("utf-8"))
    except OSError as exc:
        raise PrinterError(f"Could not reach printer at {PRINTER_IP}:{PRINTER_PORT} ({exc})") from exc

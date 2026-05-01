import os
import socket
import time

from GreeMQTT.logger import log

UDP_PORT = int(os.getenv("UDP_PORT", 7000))
SOCKET_TIMEOUT = 5
BROADCAST_TIMEOUT = 3
SCAN_PACKET = b'{"t":"scan"}'


def send_udp(device_ip: str, request: bytes, retries: int = 3) -> bytes | None:
    for attempt in range(retries):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            try:
                sock.sendto(request, (device_ip, UDP_PORT))
                data, _ = sock.recvfrom(65535)
                return data or None
            except socket.timeout:
                pass
            except OSError as e:
                log.warning("UDP error", ip=device_ip, error=str(e))
                break
        if attempt < retries - 1:
            time.sleep(0.5)
    log.warning("UDP send failed", ip=device_ip)
    return None


def scan_device(ip: str) -> bytes | None:
    """Send a scan packet to a specific IP and return the response."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(SOCKET_TIMEOUT)
        try:
            sock.sendto(SCAN_PACKET, (ip, UDP_PORT))
            data, _ = sock.recvfrom(65535)
            return data or None
        except socket.timeout:
            return None
        except OSError as e:
            log.error("Scan failed", ip=ip, error=str(e))
            return None


def discover_devices(broadcast_address: str) -> list[tuple[bytes, str]]:
    """Broadcast scan and collect all responses."""
    results: list[tuple[bytes, str]] = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(BROADCAST_TIMEOUT)
        try:
            sock.bind(("0.0.0.0", 0))
            sock.sendto(SCAN_PACKET, (broadcast_address, UDP_PORT))
            log.info("Broadcast scan sent", address=broadcast_address)
            while True:
                try:
                    data, addr = sock.recvfrom(65535)
                    if data:
                        results.append((data, addr[0]))
                except socket.timeout:
                    break
        except OSError as e:
            log.error("Broadcast discovery failed", address=broadcast_address, error=str(e))
    log.info("Discovery complete", devices_found=len(results))
    return results

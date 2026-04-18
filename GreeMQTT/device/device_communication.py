import os
import socket
import time
from typing import Optional

from GreeMQTT.logger import log

UDP_PORT = int(os.getenv("UDP_PORT", 7000))
SOCKET_TIMEOUT = 5
MAX_RETRIES = 3
RETRY_DELAY = 0.5


class DeviceCommunicator:
    def __init__(self, device_ip: str):
        self.device_ip = device_ip

    def send_data(
        self,
        request: bytes,
        udp_port: int = UDP_PORT,
    ) -> Optional[bytes]:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(SOCKET_TIMEOUT)
            try:
                sock.sendto(request, (self.device_ip, udp_port))
                data, addr = sock.recvfrom(65535)
                return data if data else None
            except socket.timeout as e:
                last_error = e
            except OSError as e:
                last_error = e
            finally:
                sock.close()
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                log.debug("Retrying UDP send", ip=self.device_ip, attempt=attempt + 1)

        log.warning("UDP send failed after retries", ip=self.device_ip, retries=MAX_RETRIES,
                     error=str(last_error) if last_error else "unknown")
        return None

    @staticmethod
    def broadcast_scan(
        target_ip: str,
        udp_port: int = UDP_PORT,
    ) -> Optional[bytes]:
        is_broadcast = target_ip.endswith(".255")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(SOCKET_TIMEOUT)
        try:
            if is_broadcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.bind(("0.0.0.0", 0))
            sock.sendto(b'{"t":"scan"}', (target_ip, udp_port))
            data, addr = sock.recvfrom(65535)
            return data if data else None
        except socket.timeout:
            return None
        except (OSError, ConnectionError) as e:
            log.error("Failed to create scan endpoint", target_ip=target_ip, error=str(e))
            return None
        finally:
            sock.close()

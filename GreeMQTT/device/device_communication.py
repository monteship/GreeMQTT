import os
import socket
import time

from GreeMQTT.logger import log

UDP_PORT = int(os.getenv("UDP_PORT", 7000))
SOCKET_TIMEOUT = 5
MAX_RETRIES = 3
RETRY_DELAY = 0.5
BROADCAST_SCAN_TIMEOUT = 3


class DeviceCommunicator:
    def __init__(self, device_ip: str):
        self.device_ip = device_ip

    def send_data(
        self,
        request: bytes,
        udp_port: int = UDP_PORT,
    ) -> bytes | None:
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
    ) -> bytes | None:
        """Send a scan packet to a single IP and return the response."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(SOCKET_TIMEOUT)
        try:
            if target_ip.endswith(".255"):
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

    @staticmethod
    def broadcast_discovery(
        broadcast_address: str = "192.168.1.255",
        udp_port: int = UDP_PORT,
        timeout: float = BROADCAST_SCAN_TIMEOUT,
    ) -> list[tuple[bytes, str]]:
        """Send a single broadcast scan and collect all responses.

        Returns a list of (raw_response_bytes, ip_address) tuples.
        """
        results: list[tuple[bytes, str]] = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        try:
            sock.bind(("0.0.0.0", 0))
            sock.sendto(b'{"t":"scan"}', (broadcast_address, udp_port))
            log.info("Broadcast scan sent", address=broadcast_address, port=udp_port)

            while True:
                try:
                    data, addr = sock.recvfrom(65535)
                    if data:
                        results.append((data, addr[0]))
                        log.debug("Broadcast response received", ip=addr[0])
                except socket.timeout:
                    break
        except (OSError, ConnectionError) as e:
            log.error("Broadcast discovery failed", address=broadcast_address, error=str(e))
        finally:
            sock.close()

        log.info("Broadcast discovery complete", devices_found=len(results))
        return results


import asyncio
import os
import socket
from typing import Optional

UDP_PORT = int(os.getenv("UDP_PORT", 7000))
SOCKET_TIMEOUT = 5


class DeviceCommunicator:
    def __init__(self, device_ip: str):
        self.device_ip = device_ip

    async def send_data(
        self,
        request: bytes,
        udp_port: int = UDP_PORT,
    ) -> Optional[bytes]:
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        response_data = bytearray()

        class UDPClientProtocol(asyncio.DatagramProtocol):
            def __init__(self, ip):
                self.transport = None
                self.ip = ip

            def connection_made(self, transport):
                self.transport = transport
                self.transport.sendto(request, (self.ip, udp_port))

            def datagram_received(self, data, addr):
                response_data.extend(data)
                on_con_lost.set_result(True)
                self.transport.close()

            def error_received(self, exc):
                on_con_lost.set_result(False)
                self.transport.close()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPClientProtocol(self.device_ip),
            remote_addr=(self.device_ip, udp_port),
        )
        try:
            await asyncio.wait_for(on_con_lost, timeout=SOCKET_TIMEOUT)
        except asyncio.TimeoutError:
            transport.close()
            return None
        return bytes(response_data) if response_data else None

    @staticmethod
    async def broadcast_scan(
        target_ip: str,
        udp_port: int = UDP_PORT,
    ) -> Optional[bytes]:
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        response_data = bytearray()

        # Determine if this is a broadcast IP (ends with .255) or a specific IP
        is_broadcast = target_ip.endswith(".255")

        class UDPScanProtocol(asyncio.DatagramProtocol):
            def connection_made(self, transport):
                sock = transport.get_extra_info("socket")
                # Only set broadcast flag for actual broadcast addresses
                if is_broadcast:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.transport = transport
                self.transport.sendto(b'{"t":"scan"}', (target_ip, udp_port))

            def datagram_received(self, data, addr):
                response_data.extend(data)
                on_con_lost.set_result(True)
                self.transport.close()

            def error_received(self, exc):
                on_con_lost.set_result(False)
                self.transport.close()

        if is_broadcast:
            # For broadcast, bind to any local address
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: UDPScanProtocol(),
                local_addr=("0.0.0.0", 0),
            )
        else:
            # For specific IP, use direct connection
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: UDPScanProtocol(),
                remote_addr=(target_ip, udp_port),
            )

        try:
            await asyncio.wait_for(on_con_lost, timeout=SOCKET_TIMEOUT)
        except asyncio.TimeoutError:
            transport.close()
            return None
        return bytes(response_data) if response_data else None

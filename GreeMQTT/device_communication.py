import asyncio
from typing import Optional

UDP_PORT = 7000
SOCKET_TIMEOUT = 5


class DeviceCommunicator:
    def __init__(self, device_ip: str):
        self.device_ip = device_ip

    async def send_data(self, request: bytes) -> Optional[bytes]:
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        response_data = bytearray()

        class UDPClientProtocol(asyncio.DatagramProtocol):
            def __init__(self, ip):
                self.transport = None
                self.ip = ip

            def connection_made(self, transport):
                self.transport = transport
                self.transport.sendto(request, (self.ip, UDP_PORT))

            def datagram_received(self, data, addr):
                response_data.extend(data)
                on_con_lost.set_result(True)
                self.transport.close()

            def error_received(self, exc):
                on_con_lost.set_result(False)
                self.transport.close()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPClientProtocol(self.device_ip),
            remote_addr=(self.device_ip, UDP_PORT),
        )
        try:
            await asyncio.wait_for(on_con_lost, timeout=SOCKET_TIMEOUT)
        except asyncio.TimeoutError:
            transport.close()
            return None
        return bytes(response_data) if response_data else None

    @staticmethod
    async def broadcast_scan(ip_address: str) -> Optional[bytes]:
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        response_data = bytearray()

        class UDPBroadcastProtocol(asyncio.DatagramProtocol):
            def __init__(self):
                self.transport = None

            def connection_made(self, transport):
                self.transport = transport
                self.transport.sendto(b'{"t":"scan"}', (ip_address, UDP_PORT))

            def datagram_received(self, data, addr):
                response_data.extend(data)
                on_con_lost.set_result(True)
                self.transport.close()

            def error_received(self, exc):
                on_con_lost.set_result(False)
                self.transport.close()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPBroadcastProtocol(),
            remote_addr=(ip_address, UDP_PORT),
        )
        try:
            await asyncio.wait_for(on_con_lost, timeout=SOCKET_TIMEOUT)
        except asyncio.TimeoutError:
            transport.close()
            return None
        return bytes(response_data) if response_data else None

import asyncio
import json
import logging

from config import STRATUM_HOST, STRATUM_PORT
from rpc import BitcoinRPCError, call_rpc

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("stratum")


class StratumServer:
    def __init__(self):
        self.connections = set()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        self.connections.add(writer)
        LOGGER.info("Client connected: %s", addr)
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode("utf-8").strip()
                if not message:
                    continue
                try:
                    request = json.loads(message)
                except json.JSONDecodeError:
                    await self.send_error(writer, None, "Invalid JSON")
                    continue
                await self.dispatch(request, writer)
        finally:
            self.connections.discard(writer)
            writer.close()
            await writer.wait_closed()
            LOGGER.info("Client disconnected: %s", addr)

    async def dispatch(self, request, writer):
        method = request.get("method")
        request_id = request.get("id")
        if method == "mining.subscribe":
            await self.send_result(writer, request_id, [None, "pool_sha256d"])
        elif method == "mining.authorize":
            await self.send_result(writer, request_id, True)
        elif method == "mining.submit":
            await self.handle_submit(request, writer)
        else:
            await self.send_error(writer, request_id, "Unknown method")

    async def handle_submit(self, request, writer):
        request_id = request.get("id")
        params = request.get("params", [])
        LOGGER.info("Received share: %s", params)
        # The pool intentionally avoids reporting hash rate to Bitcoin Core.
        # We only submit full blocks if needed, without using getnetworkhashps.
        try:
            if len(params) >= 3:
                block_hex = params[-1]
                call_rpc("submitblock", [block_hex])
        except BitcoinRPCError as exc:
            LOGGER.warning("submitblock failed: %s", exc)
        await self.send_result(writer, request_id, True)

    async def send_result(self, writer, request_id, result):
        response = json.dumps({"id": request_id, "result": result, "error": None})
        writer.write((response + "\n").encode("utf-8"))
        await writer.drain()

    async def send_error(self, writer, request_id, message):
        response = json.dumps({"id": request_id, "result": None, "error": message})
        writer.write((response + "\n").encode("utf-8"))
        await writer.drain()


async def main():
    server = StratumServer()
    srv = await asyncio.start_server(server.handle_client, STRATUM_HOST, STRATUM_PORT)
    addresses = ", ".join(str(sock.getsockname()) for sock in srv.sockets)
    LOGGER.info("Stratum server listening on %s", addresses)
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

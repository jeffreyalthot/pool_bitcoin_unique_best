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
        self.pool_state = None

    def collect_pool_state(self):
        best_hash = call_rpc("getbestblockhash")
        header = call_rpc("getblockheader", [best_hash, True])
        difficulty = call_rpc("getdifficulty")
        template = call_rpc("getblocktemplate", [{"rules": ["segwit"]}])
        priorities = call_rpc("getprioritisedtransactions")
        return {
            "height": header.get("height"),
            "best_hash": best_hash,
            "difficulty": difficulty,
            "template_height": template.get("height"),
            "prioritised_tx_count": len(priorities),
        }

    async def refresh_pool_state(self):
        try:
            self.pool_state = await asyncio.to_thread(self.collect_pool_state)
            LOGGER.info(
                "Pool state updated: height=%s difficulty=%s",
                self.pool_state.get("height"),
                self.pool_state.get("difficulty"),
            )
        except BitcoinRPCError as exc:
            LOGGER.warning("Pool state refresh failed: %s", exc)

    def is_valid_block(self, block_hex):
        try:
            result = call_rpc("testblockvalidity", [block_hex])
        except BitcoinRPCError as exc:
            LOGGER.warning("testblockvalidity failed: %s", exc)
            return False
        if isinstance(result, bool):
            return result
        if isinstance(result, dict):
            return result.get("valid", False)
        return False

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
            await self.refresh_pool_state()
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
                if self.is_valid_block(block_hex):
                    result = call_rpc("submitblock", [block_hex])
                    if result is not None:
                        LOGGER.warning("submitblock rejected: %s", result)
                else:
                    LOGGER.info("Skipping submitblock for invalid block candidate.")
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

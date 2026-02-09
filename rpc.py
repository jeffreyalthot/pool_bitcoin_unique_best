import base64
import json
import urllib.request

from config import RPC_HOST, RPC_PORT, RPC_USER, RPC_PASSWORD


class BitcoinRPCError(RuntimeError):
    pass


def _rpc_url():
    return f"http://{RPC_HOST}:{RPC_PORT}"


def call_rpc(method, params=None):
    if params is None:
        params = []
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    credentials = f"{RPC_USER}:{RPC_PASSWORD}".encode("utf-8")
    auth_header = base64.b64encode(credentials).decode("utf-8")
    request = urllib.request.Request(_rpc_url(), data=payload)
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Basic {auth_header}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise BitcoinRPCError(f"RPC connection failed: {exc}") from exc
    data = json.loads(body)
    if data.get("error"):
        raise BitcoinRPCError(data["error"])
    return data.get("result")


def get_block_template(template_request):
    return call_rpc("getblocktemplate", [template_request])


def get_mining_info():
    return call_rpc("getmininginfo")


def get_network_hash_ps(nblocks=120, height=-1):
    return call_rpc("getnetworkhashps", [nblocks, height])


def get_prioritised_transactions():
    return call_rpc("getprioritisedtransactions")


def prioritise_transaction(txid, fee_delta, dummy=0):
    return call_rpc("prioritisetransaction", [txid, dummy, fee_delta])


def submit_block(hexdata, dummy="ignored"):
    return call_rpc("submitblock", [hexdata, dummy])


def submit_header(hexdata):
    return call_rpc("submitheader", [hexdata])

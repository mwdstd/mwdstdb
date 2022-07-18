from os import environ
from httpx import AsyncClient, Response

calc_url = environ.get("CALC_URL")

client: AsyncClient = None

class RPCError(BaseException):
    def __init__(self, message = None):
        if(message is None):
            self.message = 'An RPC error occured'
        else:
            self.message = message

def start():
    global client
    client = AsyncClient(timeout=None)

async def post(url, request) -> Response:
    response = await client.post(f'{calc_url}{url}', json=request)
    if response.is_error:
        raise RPCError()
    return response


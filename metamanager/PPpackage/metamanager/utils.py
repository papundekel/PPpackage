from httpx import Response

from PPpackage.utils.http_stream import AsyncChunkReader


def HTTPResponseReader(response: Response):
    return AsyncChunkReader(memoryview(chunk) async for chunk in response.aiter_raw())
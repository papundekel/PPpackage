from httpx import Response

from PPpackage.utils.serialization.chunk_reader import ChunkReader


def HTTPResponseReader(response: Response):
    return ChunkReader(memoryview(chunk) async for chunk in response.aiter_raw())

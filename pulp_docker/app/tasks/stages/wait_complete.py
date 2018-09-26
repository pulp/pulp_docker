import asyncio

from stages import Stage


class WaitUntilComplete(Stage):
    """
    Does not output until previous stages are complete.
    """
    async def __call__(self, in_q, out_q):
        pending_q = asyncio.Queue()
        # Wait
        while True:
            next_in = await in_q.get()
            if next_in is None:
                break
            await pending_q.put(next_in)
        await pending_q.put(None)
        # Do
        while True:
            do_next = await pending_q.get()
            if do_next is None:
                break
            await out_q.put(do_next)
        await out_q.put(None)

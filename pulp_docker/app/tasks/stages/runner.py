import asyncio

from stages import Stage


class ConcurrentRunner(Stage):
    """
    Run any Stage concurrently.

    For each item in_q, spin up a new instance of the Stage and run them all concurrently. All
    output from the concurrent Stage is consolidated into a single out_q.
    """

    def __init__(self, stage, max_concurrent_content=5):
        """Initialize the stage."""
        self.max_concurrent_content = max_concurrent_content
        self.stage = stage

    @property
    def saturated(self):
        """
        Indicates that max concurrency has been reached.
        """
        return len(self.futures) >= self.max_concurrent_content

    async def __call__(self, in_q, out_q):
        """
        The coroutine for this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.
        Returns:
            The coroutine for this stage.

        """
        # TODO add max_concurrent
        self.futures = set()
        prev_running = True
        middle_q = asyncio.Queue()
        pull_from_queue = asyncio.ensure_future(in_q.get())
        self.futures.add(pull_from_queue)
        ready = set()
        while prev_running or self.futures:
            done, self.futures = await asyncio.wait(self.futures,
                                                    return_when=asyncio.FIRST_COMPLETED)

            done = ready.union(done)
            ready = set()
            while done:
                task = done.pop()
                # if finished task is in_q.get(), start up a new instance of the stage to run
                # and make a new task for in_q.get()
                if task is pull_from_queue:
                    if self.saturated:
                        ready.add(task)
                    else:
                        next_in = task.result()
                        if next_in is None:
                            prev_running = False
                        else:
                            single_q = SingletonQueue()
                            await single_q.put(next_in)
                            self.futures.add(asyncio.ensure_future(self.stage(single_q, middle_q)))
                            pull_from_queue = asyncio.ensure_future(in_q.get())
                            self.futures.add(pull_from_queue)

                # since we are running many instances of the stage, we need to catch the  Nones
                # they output, and transfer their out_q (middle_q) to the main out_q.
                # So, Don't pass None, dont wait on the middle_q
                while True:
                    try:
                        next_out = middle_q.get_nowait()
                    except asyncio.QueueEmpty as e:
                        break
                    else:
                        if next_out is not None:
                            await out_q.put(next_out)

        await out_q.put(None)


class SingletonQueue:
    """
    A Queue that only contains 1 item.
    """

    def __init__(self):
        """Initialize the Queue."""
        self.q = None

    async def put(self, item):
        """Put an item on the Queue."""
        self.q = item

    async def get(self):
        """Retrieve an item from the Queue."""
        item = self.q
        self.q = None
        return item

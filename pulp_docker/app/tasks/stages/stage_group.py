import asyncio

from pulpcore.plugin.stages import Stage


class StageGroup(Stage):
    """
    Encapsulates a list of Stages, allowing them to be treated as a single Stage.
    """

    def __init__(self, stages):
        """Initialize the stage."""
        self.stages = stages

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
        futures = await self.create_pipeline(in_q, out_q)
        try:
            await asyncio.gather(*futures)
        except Exception:
            # One of the stages raised an exception, cancel all stages...
            pending = []
            for task in futures:
                if not task.done():
                    task.cancel()
                    pending.append(task)
            # ...and run until all Exceptions show up
            if pending:
                await asyncio.wait(pending, timeout=60)
            raise

    async def create_pipeline(self, in_q, final_out_q):
        """
        Creates an encapsulated pipeline.

        Pass items from the in_q through the pipeline and output to the final_out_q.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            final_out_q (:class:`asyncio.Queue`): The queue to put
                :class:`~pulpcore.plugin.stages.DeclarativeContent` into.
        """
        futures = []
        last = len(self.stages) - 1
        for i, stage in enumerate(self.stages):
            if i != last:
                out_q = asyncio.Queue(maxsize=100)
            else:
                out_q = final_out_q
            futures.append(asyncio.ensure_future(stage(in_q, out_q)))
            in_q = out_q
        return futures

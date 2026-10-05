import asyncio


STARTUP_PING_RETRY_DELAYS = (0, 1, 3)


def _load_startup_ping_row(client_factory, row_loader):
    client = client_factory()
    return row_loader(9, client=client)


async def load_startup_ping_row(
    client_factory,
    row_loader,
    retry_delays=STARTUP_PING_RETRY_DELAYS,
    sleep=asyncio.sleep,
):
    """Load startup configuration without sharing or blocking the bot client."""
    last_error = None
    for delay in retry_delays:
        if delay:
            await sleep(delay)
        try:
            return await asyncio.to_thread(
                _load_startup_ping_row,
                client_factory,
                row_loader,
            )
        except Exception as exc:
            last_error = exc

    if last_error is None:
        raise ValueError("startup ping retry schedule is empty")
    raise last_error

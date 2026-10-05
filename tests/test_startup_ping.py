import unittest
from unittest.mock import AsyncMock, Mock

from src.startup_ping import load_startup_ping_row


class StartupPingTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_database_failure_is_retried_with_fresh_client(self):
        clients = [object(), object()]
        client_factory = Mock(side_effect=clients)
        row_loader = Mock(side_effect=[
            BlockingIOError(35, "Resource temporarily unavailable"),
            {"id": 9, "data": {"startup_ping_channel": "123"}},
        ])
        sleep = AsyncMock()

        row = await load_startup_ping_row(
            client_factory,
            row_loader,
            retry_delays=(0, 1, 3),
            sleep=sleep,
        )

        self.assertEqual(row["id"], 9)
        self.assertEqual(client_factory.call_count, 2)
        self.assertEqual(row_loader.call_args_list[0].kwargs, {"client": clients[0]})
        self.assertEqual(row_loader.call_args_list[1].kwargs, {"client": clients[1]})
        sleep.assert_awaited_once_with(1)

    async def test_permanent_database_failure_stops_after_three_attempts(self):
        client_factory = Mock(side_effect=[object(), object(), object()])
        error = BlockingIOError(35, "Resource temporarily unavailable")
        row_loader = Mock(side_effect=error)
        sleep = AsyncMock()

        with self.assertRaises(BlockingIOError):
            await load_startup_ping_row(
                client_factory,
                row_loader,
                retry_delays=(0, 1, 3),
                sleep=sleep,
            )

        self.assertEqual(client_factory.call_count, 3)
        self.assertEqual(row_loader.call_count, 3)
        self.assertEqual(
            [call.args for call in sleep.await_args_list],
            [(1,), (3,)],
        )

    async def test_empty_retry_schedule_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "retry schedule is empty"):
            await load_startup_ping_row(Mock(), Mock(), retry_delays=())


if __name__ == "__main__":
    unittest.main()

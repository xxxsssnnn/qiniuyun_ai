import unittest
from unittest.mock import AsyncMock

from app.services.connection_manager import ConnectionManager


class ConnectionManagerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_broadcast_removes_closed_connection_and_keeps_others(self) -> None:
        manager = ConnectionManager()
        closed_socket = AsyncMock()
        healthy_socket = AsyncMock()
        closed_socket.send_json.side_effect = RuntimeError(
            "Unexpected ASGI message 'websocket.send'"
        )
        manager._connections["session-1"].update(
            {closed_socket, healthy_socket}
        )
        message = {"type": "status", "payload": {"message": "connected"}}

        await manager.broadcast("session-1", message)

        healthy_socket.send_json.assert_awaited_once_with(message)
        self.assertNotIn(closed_socket, manager._connections["session-1"])
        self.assertIn(healthy_socket, manager._connections["session-1"])

    async def test_broadcast_cleans_up_session_when_last_connection_closed(
        self,
    ) -> None:
        manager = ConnectionManager()
        closed_socket = AsyncMock()
        closed_socket.send_json.side_effect = OSError("connection closed")
        manager._connections["session-1"].add(closed_socket)

        await manager.broadcast("session-1", {"type": "status"})

        self.assertNotIn("session-1", manager._connections)


if __name__ == "__main__":
    unittest.main()

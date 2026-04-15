from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(
    prefix="/ws",
    tags=["ws"],
)


class ConnectionManager:
    def __init__(self) -> None:
        self._dashboard_clients: list[WebSocket] = []
        self._alert_clients: list[WebSocket] = []

    async def connect_dashboard(self, ws: WebSocket) -> None:
        await ws.accept()
        self._dashboard_clients.append(ws)

    async def connect_alerts(self, ws: WebSocket) -> None:
        await ws.accept()
        self._alert_clients.append(ws)

    def disconnect_dashboard(self, ws: WebSocket) -> None:
        if ws in self._dashboard_clients:
            self._dashboard_clients.remove(ws)

    def disconnect_alerts(self, ws: WebSocket) -> None:
        if ws in self._alert_clients:
            self._alert_clients.remove(ws)

    async def broadcast_dashboard(self, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._dashboard_clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_dashboard(ws)

    async def broadcast_alert(self, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._alert_clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_alerts(ws)


manager = ConnectionManager()


@router.websocket("/dashboard")
async def wsDashboard(ws: WebSocket):
    await manager.connect_dashboard(ws)
    try:
        while True:
            # Keep connection alive; client doesn't send meaningful data
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(ws)


@router.websocket("/alerts")
async def wsAlerts(ws: WebSocket):
    await manager.connect_alerts(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_alerts(ws)

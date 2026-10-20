from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass
                
    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

manager = ConnectionManager()

async def broadcast_incident_alert(incident_data: dict, assignment=None):
    await manager.broadcast({
        "type": "INCIDENT_ALERT",
        "incident": incident_data,
        "assignment": assignment
    })

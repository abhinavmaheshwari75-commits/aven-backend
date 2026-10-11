import asyncio
import json
import websockets

WS_URL = "ws://127.0.0.1:8000/ws/aven"


async def receive_messages(websocket):
    """Listens for streaming response chunks and proactive system alerts."""
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type == "stream":
                    print(data.get("content", ""), end="", flush=True)
                elif msg_type == "end":
                    print("\n")
                elif msg_type == "alert":
                    print(f"\n\n{data.get('content')}\n")
                else:
                    print(data.get("content", message), end="", flush=True)
            except json.JSONDecodeError:
                # Handle raw text message fallback safely
                print(message, end="", flush=True)
    except websockets.exceptions.ConnectionClosed:
        print("\n[WS] Disconnected from server.")


async def send_messages(websocket):
    """Handles continuous user input from terminal."""
    loop = asyncio.get_running_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, input, "You: ")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
            print("Aven: ", end="", flush=True)
            await websocket.send(json.dumps({"message": user_input}))
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"\n[CLIENT ERROR] {e}")
            break


async def main():
    print("Connecting to Aven backend...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("Connected to Aven (Level 6 Autonomous WebSocket Channel).")
            print(
                "Type your message below. Proactive alerts will appear"
                " automatically.\n"
            )

            receive_task = asyncio.create_task(receive_messages(websocket))
            send_task = asyncio.create_task(send_messages(websocket))

            done, pending = await asyncio.wait(
                [receive_task, send_task], return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import time
import psutil

LAST_ALERT_TIME = 0
ALERT_COOLDOWN = 60  # seconds between warnings


async def monitor_system_resources(websocket_manager):
    global LAST_ALERT_TIME
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            current_time = time.time()

            if (cpu > 90 or ram > 90) and (current_time - LAST_ALERT_TIME > ALERT_COOLDOWN):
                LAST_ALERT_TIME = current_time
                alert_msg = f"⚠️ Resource Alert: High system load detected (CPU: {cpu}%, RAM: {ram}%)."
                await websocket_manager.broadcast_alert(alert_msg)

        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")

        await asyncio.sleep(5)
import os
import sys
import subprocess
import webbrowser
import tempfile
import psutil
import pyautogui
from PIL import Image

# Check for Tesseract OCR availability for screen text extraction
try:
    import pytesseract
    # Default Windows installation path for Tesseract OCR
    tesseract_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_win_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_win_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# -------------------------------------------------------------------------
# System Tool Implementations
# -------------------------------------------------------------------------

def open_application(app_name: str) -> str:
    """Launches a desktop application or system utility by name."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(f"start {app_name}", shell=True)
        else:
            subprocess.Popen([app_name])
        return f"Successfully launched {app_name}."
    except Exception as e:
        return f"Failed to launch {app_name}: {str(e)}"


def adjust_volume(action: str) -> str:
    """Adjusts system volume up, down, or toggles mute."""
    try:
        action_lower = action.lower()
        if action_lower == "up":
            pyautogui.press("volumeup", presses=5)
            return "Increased system volume."
        elif action_lower == "down":
            pyautogui.press("volumedown", presses=5)
            return "Decreased system volume."
        elif action_lower == "mute":
            pyautogui.press("volumemute")
            return "Toggled system volume mute."
        else:
            return f"Unknown action: '{action}'. Use 'up', 'down', or 'mute'."
    except Exception as e:
        return f"Failed to adjust volume: {str(e)}"


def open_url(url: str) -> str:
    """Opens a website URL in the default web browser."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Failed to open URL: {str(e)}"


def get_system_health() -> str:
    """Retrieves CPU utilization, RAM usage, and battery metrics."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        battery = psutil.sensors_battery()

        ram_used_gb = round(ram.used / (1024**3), 2)
        ram_total_gb = round(ram.total / (1024**3), 2)

        health_report = (
            f"CPU Usage: {cpu}%\n"
            f"RAM Usage: {ram.percent}% ({ram_used_gb} GB / {ram_total_gb} GB)"
        )
        if battery:
            plugged_status = "Plugged in" if battery.power_plugged else "Discharging"
            health_report += f"\nBattery: {battery.percent}% ({plugged_status})"

        return health_report
    except Exception as e:
        return f"Failed to retrieve system health: {str(e)}"


def execute_shell_command(command: str) -> str:
    """Executes a command prompt / powershell shell command."""
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = res.stdout if res.stdout else res.stderr
        return output.strip() if output else "Command executed successfully with no output."
    except Exception as e:
        return f"Execution error: {str(e)}"


def capture_screen(filename: str = "latest_screenshot.png") -> str:
    """Captures the primary monitor screen, saves the image to system temp, and extracts text via OCR."""
    try:
        # Save to system temp folder to prevent Uvicorn hot-reload triggers
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)

        width, height = screenshot.size
        result_summary = f"Screenshot saved to '{filepath}' (Resolution: {width}x{height})."

        if HAS_OCR:
            try:
                extracted_text = pytesseract.image_to_string(screenshot).strip()
                if extracted_text:
                    clean_text = extracted_text[:2000]
                    result_summary += f"\n\n--- VISIBLE SCREEN TEXT (OCR) ---\n{clean_text}"
                else:
                    result_summary += "\n\n[OCR Notice: No readable text detected on screen.]"
            except Exception as ocr_err:
                result_summary += f"\n\n[OCR Notice: Text extraction skipped or Tesseract not configured. Error: {ocr_err}]"

        return result_summary
    except Exception as e:
        return f"Failed to capture screen: {str(e)}"


# -------------------------------------------------------------------------
# Tool Schemas & Function Dispatcher
# -------------------------------------------------------------------------

SYSTEM_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Launches a desktop application or system tool by name (e.g. notepad, calc, chrome).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application command or executable name."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_volume",
            "description": "Adjusts or mutes the system audio volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["up", "down", "mute"],
                        "description": "Volume action to perform."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Opens a web link or URL in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The complete web URL to open."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_health",
            "description": "Checks and returns CPU, RAM, and battery metrics.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell_command",
            "description": "Executes a shell or command prompt instruction directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The terminal command string."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screen",
            "description": "Takes a screenshot of the user's primary monitor to view active windows or read screen text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Optional custom file name for saving the image."
                    }
                },
                "required": []
            }
        }
    }
]

SYSTEM_TOOLS = {
    "open_application": open_application,
    "adjust_volume": adjust_volume,
    "open_url": open_url,
    "get_system_health": get_system_health,
    "execute_shell_command": execute_shell_command,
    "capture_screen": capture_screen
}
import json
import threading
import tkinter as tk
import customtkinter as ctk
import websocket

# Configuration & Styling
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

WS_URL = "ws://127.0.0.1:8000/ws/aven"


class AvenGUIOverlay(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Aven AI")
        self.geometry("420x520+1400+200")
        self.attributes("-topmost", True)
        self.overrideredirect(True)  # Frameless floating window
        self.configure(fg_color="#0F0F12")

        # Draggable setup variables
        self._offset_x = 0
        self._offset_y = 0

        # UI Layout
        self._build_header()
        self._build_chat_display()
        self._build_status_bar()
        self._build_input_bar()

        # Bind window dragging events
        self.header_frame.bind("<Button-1>", self._click_window)
        self.header_frame.bind("<B1-Motion>", self._drag_window)
        self.title_label.bind("<Button-1>", self._click_window)
        self.title_label.bind("<B1-Motion>", self._drag_window)

        # WebSocket state
        self.ws = None
        self.ws_thread = None
        self.connect_websocket()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(
            self, fg_color="#18181C", corner_radius=10, height=45
        )
        self.header_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="⚡ AVEN AI",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00E5FF",
        )
        self.title_label.pack(side="left", padx=15, pady=8)

        self.close_btn = ctk.CTkButton(
            self.header_frame,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#FF4D4D",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.destroy,
        )
        self.close_btn.pack(side="right", padx=8)

        self.minimize_btn = ctk.CTkButton(
            self.header_frame,
            text="—",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#2A2A35",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.iconify,
        )
        self.minimize_btn.pack(side="right", padx=2)

    def _build_chat_display(self):
        self.chat_box = ctk.CTkTextbox(
            self,
            fg_color="#131317",
            text_color="#E0E0E0",
            font=ctk.CTkFont(size=13),
            corner_radius=10,
            wrap="word",
        )
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=5)
        self.chat_box.configure(state="disabled")

    def _build_status_bar(self):
        self.status_frame = ctk.CTkFrame(
            self, fg_color="transparent", height=20
        )
        self.status_frame.pack(fill="x", padx=15, pady=2)

        self.status_indicator = ctk.CTkLabel(
            self.status_frame,
            text="● Disconnected",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FF5555",
        )
        self.status_indicator.pack(side="left")

    def _build_input_bar(self):
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Type command or query...",
            fg_color="#18181C",
            border_color="#2B2B36",
            text_color="#FFFFFF",
            corner_radius=8,
            height=38,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda event: self.send_text_message())

        self.send_btn = ctk.CTkButton(
            self.input_frame,
            text="Send",
            width=65,
            height=38,
            corner_radius=8,
            fg_color="#00E5FF",
            text_color="#000000",
            hover_color="#00B2CC",
            font=ctk.CTkFont(weight="bold"),
            command=self.send_text_message,
        )
        self.send_btn.pack(side="right")

    # Dragging logic for frameless window
    def _click_window(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _drag_window(self, event):
        x = self.winfo_pointerx() - self._offset_x
        y = self.winfo_pointery() - self._offset_y
        self.geometry(f"+{x}+{y}")

    # Log Message Utility
    def append_chat(self, sender: str, message: str):
        self.chat_box.configure(state="normal")
        if sender == "User":
            self.chat_box.insert("end", f"\nYou: {message}\n", "user")
        elif sender == "Aven":
            self.chat_box.insert("end", f"{message}", "aven")
        elif sender == "System":
            self.chat_box.insert("end", f"\n{message}\n", "system")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    # WebSocket Logic
    def connect_websocket(self):
        def run_ws():
            self.ws = websocket.WebSocketApp(
                WS_URL,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close,
            )
            self.ws.run_forever()

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def on_ws_open(self, ws):
        self.status_indicator.configure(
            text="● System Online", text_color="#00FF88"
        )
        self.append_chat(
            "System", "[SYSTEM] Connected to Aven Core via WebSocket."
        )

    def on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "stream":
                content = data.get("content", "")
                self.append_chat("Aven", content)
            elif msg_type == "end":
                self.append_chat("Aven", "\n")
            elif msg_type == "alert":
                alert = data.get("content", "")
                self.append_chat("System", f"[ALERT] {alert}")
        except Exception as e:
            print(f"[GUI WS ERR] {e}")

    def on_ws_error(self, ws, error):
        self.status_indicator.configure(
            text="● Error", text_color="#FF4D4D"
        )

    def on_ws_close(self, ws, close_status_code, close_msg):
        self.status_indicator.configure(
            text="● Disconnected", text_color="#FF5555"
        )

    def send_text_message(self):
        text = self.entry.get().strip()
        if text and self.ws and self.ws.sock and self.ws.sock.connected:
            self.append_chat("User", text)
            self.entry.delete(0, "end")
            payload = json.dumps({"message": text})
            self.ws.send(payload)


if __name__ == "__main__":
    app = AvenGUIOverlay()
    app.mainloop()
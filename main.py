"""
SAMP Launcher Mobile - launcher de servidores SA-MP para Android/iOS (Kivy)
Lista de favoritos, ping/players em tempo real, nickname salvo,
conexão rápida e tentativa de abrir o servidor via URI scheme (samp://).

Requisitos para rodar/empacotar:
  pip install kivy pyjnius plyer
  (Android) buildozer init && buildozer -v android debug

Este app roda também no desktop (python main.py) para testes,
já que Kivy é multiplataforma.
"""

import json
import os
import socket
import struct
import threading
import time
import webbrowser

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.metrics import dp

CONFIG_FILE = os.path.join(App.get_running_app().user_data_dir if App.get_running_app()
                            else os.path.dirname(os.path.abspath(__file__)),
                            "samp_launcher_config.json")

DEFAULT_CONFIG = {
    "nickname": "Player",
    "servers": [
        {"name": "Exemplo - adicione o seu", "ip": "127.0.0.1", "port": 7777}
    ]
}


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Protocolo de query UDP do SA-MP (opcode 'i')
# ---------------------------------------------------------------------------
def query_server_info(ip, port, timeout=1.2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        resolved = socket.gethostbyname(ip)
        packet = b"SAMP" + socket.inet_aton(resolved) + struct.pack("<H", int(port)) + b"i"
        start = time.time()
        sock.sendto(packet, (ip, int(port)))
        data, _ = sock.recvfrom(4096)
        ping_ms = round((time.time() - start) * 1000)

        offset = 11
        password = data[offset]
        offset += 1
        players, maxplayers = struct.unpack_from("<HH", data, offset)
        offset += 4

        def read_str():
            nonlocal offset
            (length,) = struct.unpack_from("<I", data, offset)
            offset += 4
            s = data[offset:offset + length].decode("utf-8", errors="replace")
            offset += length
            return s

        hostname = read_str()
        gamemode = read_str()
        read_str()  # language, não usado na UI mobile

        return {
            "online": True,
            "hostname": hostname,
            "gamemode": gamemode,
            "players": players,
            "maxplayers": maxplayers,
            "password": bool(password),
            "ping": ping_ms,
        }
    except Exception:
        return {"online": False}
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# UI (KV language)
# ---------------------------------------------------------------------------
KV = """
#:import dp kivy.metrics.dp

<ServerRow@BoxLayout>:
    name: ""
    address: ""
    status: "..."
    players: "-"
    ping: "-"
    gamemode: "-"
    orientation: "vertical"
    size_hint_y: None
    height: dp(78)
    padding: dp(12), dp(8)
    canvas.before:
        Color:
            rgba: (0.13, 0.13, 0.16, 1)
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: (0.22, 0.22, 0.26, 1)
        Line:
            points: [self.x, self.y, self.x + self.width, self.y]
            width: 0.6

    BoxLayout:
        size_hint_y: None
        height: dp(24)
        Label:
            text: root.name
            bold: True
            font_size: '16sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        Label:
            text: root.status
            color: (0.3, 0.85, 0.4, 1) if root.status == "Online" else (0.9, 0.3, 0.3, 1)
            size_hint_x: None
            width: dp(70)
            font_size: '13sp'
            bold: True

    BoxLayout:
        size_hint_y: None
        height: dp(20)
        Label:
            text: root.address
            color: (0.65, 0.65, 0.7, 1)
            font_size: '12sp'
            halign: 'left'
            text_size: self.size
        Label:
            text: root.gamemode
            color: (0.65, 0.65, 0.7, 1)
            font_size: '12sp'
            halign: 'right'
            text_size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(20)
        Label:
            text: "Players: " + root.players
            font_size: '12sp'
            color: (0.85, 0.85, 0.9, 1)
            halign: 'left'
            text_size: self.size
        Label:
            text: "Ping: " + root.ping
            font_size: '12sp'
            color: (0.85, 0.85, 0.9, 1)
            halign: 'right'
            text_size: self.size


<MainScreen>:
    BoxLayout:
        orientation: "vertical"

        # Top bar
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: dp(10), dp(6)
            spacing: dp(8)
            canvas.before:
                Color:
                    rgba: (0.09, 0.09, 0.11, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: "SAMP Launcher"
                bold: True
                font_size: '18sp'
            Widget:
            Button:
                text: "Nick: " + app.nickname
                size_hint_x: None
                width: dp(150)
                on_release: app.open_nick_dialog()

        # Quick connect
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            padding: dp(10), dp(4)
            spacing: dp(6)
            TextInput:
                id: quick_input
                hint_text: "ip:porta (conexão rápida)"
                multiline: False
                font_size: '14sp'
            Button:
                text: "Ir"
                size_hint_x: None
                width: dp(60)
                on_release: app.quick_connect(quick_input.text)

        # Server list
        RecycleView:
            id: rv
            viewclass: "ServerRow"
            RecycleBoxLayout:
                default_size: None, dp(78)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: "vertical"

        # Bottom actions
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: dp(8)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: (0.09, 0.09, 0.11, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: "+ Adicionar"
                on_release: app.open_add_dialog()
            Button:
                text: "Atualizar"
                on_release: app.refresh_all()
            Button:
                text: "Remover"
                on_release: app.remove_selected()

        Label:
            id: status_label
            text: app.status_text
            size_hint_y: None
            height: dp(28)
            font_size: '12sp'
            color: (0.6, 0.6, 0.65, 1)
"""


class MainScreen(Screen):
    pass


class SampLauncherApp(App):
    nickname = StringProperty("Player")
    status_text = StringProperty("Pronto.")
    selected_index = None

    def build(self):
        global CONFIG_FILE
        CONFIG_FILE = os.path.join(self.user_data_dir, "samp_launcher_config.json")
        self.cfg = load_config()
        self.nickname = self.cfg.get("nickname", "Player")
        self.title = "SAMP Launcher"

        self.sm = ScreenManager()
        Builder.load_string(KV)
        self.main_screen = MainScreen(name="main")
        self.sm.add_widget(self.main_screen)

        Clock.schedule_once(lambda dt: self.refresh_all(), 0.3)
        return self.sm

    # ---------------- lista/dados ----------------
    def _rv(self):
        return self.main_screen.ids.rv

    def _rebuild_rv(self):
        data = []
        for srv in self.cfg["servers"]:
            data.append({
                "name": srv["name"],
                "address": f'{srv["ip"]}:{srv["port"]}',
                "status": srv.get("_status", "..."),
                "players": srv.get("_players", "-"),
                "ping": srv.get("_ping", "-"),
                "gamemode": srv.get("_gamemode", "-"),
            })
        self._rv().data = data

    def refresh_all(self):
        self._rebuild_rv()
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        self._set_status("Consultando servidores...")
        for srv in self.cfg["servers"]:
            info = query_server_info(srv["ip"], srv["port"])
            if info and info.get("online"):
                srv["_status"] = "Online"
                srv["_players"] = f'{info["players"]}/{info["maxplayers"]}'
                srv["_ping"] = f'{info["ping"]}ms'
                srv["_gamemode"] = info["gamemode"]
            else:
                srv["_status"] = "Offline"
                srv["_players"] = "-"
                srv["_ping"] = "-"
                srv["_gamemode"] = "-"
            self._update_rv_threadsafe()
        self._set_status("Atualizado.")

    @mainthread
    def _update_rv_threadsafe(self):
        self._rebuild_rv()

    @mainthread
    def _set_status(self, text):
        self.status_text = text

    # ---------------- diálogos ----------------
    def open_nick_dialog(self):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        ti = TextInput(text=self.nickname, multiline=False, size_hint_y=None, height=dp(44))
        content.add_widget(ti)
        btn = Button(text="Salvar", size_hint_y=None, height=dp(44))
        content.add_widget(btn)
        popup = ModalView(size_hint=(0.8, 0.3))
        popup.add_widget(content)

        def save(_):
            self.nickname = ti.text.strip() or "Player"
            self.cfg["nickname"] = self.nickname
            save_config(self.cfg)
            popup.dismiss()

        btn.bind(on_release=save)
        popup.open()

    def open_add_dialog(self):
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        name_in = TextInput(hint_text="Nome do servidor", multiline=False, size_hint_y=None, height=dp(44))
        ip_in = TextInput(hint_text="IP", multiline=False, size_hint_y=None, height=dp(44))
        port_in = TextInput(hint_text="Porta", text="7777", multiline=False, size_hint_y=None, height=dp(44))
        err = Label(text="", color=(0.9, 0.3, 0.3, 1), size_hint_y=None, height=dp(20))
        add_btn = Button(text="Adicionar", size_hint_y=None, height=dp(44))

        for w in (name_in, ip_in, port_in, err, add_btn):
            content.add_widget(w)

        popup = ModalView(size_hint=(0.85, 0.55))
        popup.add_widget(content)

        def confirm(_):
            ip = ip_in.text.strip()
            port = port_in.text.strip()
            if not ip or not port.isdigit():
                err.text = "Preencha IP e porta corretamente."
                return
            self.cfg["servers"].append({
                "name": name_in.text.strip() or ip,
                "ip": ip,
                "port": int(port),
            })
            save_config(self.cfg)
            popup.dismiss()
            self.refresh_all()

        add_btn.bind(on_release=confirm)
        popup.open()

    def remove_selected(self):
        # Toque-e-segure/seleção simplificada: remove o último item consultado
        # Para produção, adicione seleção por toque no ServerRow (on_touch_down).
        if not self.cfg["servers"]:
            return
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        content.add_widget(Label(text="Remover o último servidor da lista?"))
        btn = Button(text="Remover", size_hint_y=None, height=dp(44))
        content.add_widget(btn)
        popup = ModalView(size_hint=(0.8, 0.3))
        popup.add_widget(content)

        def do_remove(_):
            self.cfg["servers"].pop()
            save_config(self.cfg)
            self._rebuild_rv()
            popup.dismiss()

        btn.bind(on_release=do_remove)
        popup.open()

    # ---------------- conexão ----------------
    def quick_connect(self, text):
        text = text.strip()
        if ":" not in text:
            self._set_status("Use o formato ip:porta")
            return
        ip, port = text.split(":", 1)
        if not port.isdigit():
            self._set_status("Porta inválida.")
            return
        self._launch(ip.strip(), int(port.strip()))

    def _launch(self, ip, port):
        nickname = self.nickname
        address = f"{ip}:{port}"

        # 1) tenta abrir via URI scheme (clientes mobile compatíveis registram "samp://")
        uri = f"samp://{address}?nick={nickname}"
        try:
            webbrowser.open(uri)
            opened = True
        except Exception:
            opened = False

        # 2) fallback: copia o endereço para a área de transferência
        Clipboard.copy(address)

        if opened:
            self._set_status(f"Tentando abrir {address} (samp://). Endereço também copiado.")
        else:
            self._set_status(f"Endereço {address} copiado. Cole no seu cliente SA-MP mobile.")


if __name__ == "__main__":
    SampLauncherApp().run()

import math
import sys
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import requests

class CardMock:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

class BoardPopup:
    def __init__(self, parent, client, title="ポーカー実況・チャット掲示板"):
        self.parent = parent
        self.client = client
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("380x550")
        
        self.window.update_idletasks()
        x = parent.winfo_x() + parent.winfo_width() + 10
        y = parent.winfo_y()
        self.window.geometry(f"+{x}+{y}")
        
        self.label = tk.Label(self.window, text="💬 リアルタイムチャット掲示板", font=("Arial", 11, "bold"), pady=10)
        self.label.pack()
        
        self.text_area = scrolledtext.ScrolledText(self.window, wrap=tk.WORD, width=40, height=22, font=("MS Gothic", 10), bg="#f4f6f9", fg="#2c3e50")
        self.text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.config(state=tk.DISABLED)
        
        input_frame = tk.Frame(self.window)
        input_frame.pack(padx=10, pady=10, fill=tk.X, side=tk.BOTTOM)
        
        self.entry = tk.Entry(input_frame, font=("MS Gothic", 10))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self.send_message())
        
        self.send_btn = tk.Button(input_frame, text="送信", command=self.send_message, bg="#4caf50", fg="white", font=("Arial", 9, "bold"))
        self.send_btn.pack(side=tk.RIGHT)

    def update_chat_logs(self, logs):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        for log in logs:
            self.text_area.insert(tk.END, f" {log}\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def send_message(self):
        msg = self.entry.get().strip()
        if msg:
            if self.client.is_cpu_mode:
                # CPUモードの時はローカルチャットに流す
                self.client.local_room.chat_logs.append(f"【{self.client.player_name}】: {msg}")
                self.entry.delete(0, tk.END)
            else:
                try:
                    requests.post(f"{self.client.server_url}/chat", json={
                        "room_id": self.client.room_id,
                        "name": self.client.player_name,
                        "message": msg
                    })
                    self.entry.delete(0, tk.END)
                except:
                    pass

class TexasHoldemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("♠♥♦♣ テキサスホールデム・ポーカー ♣♦♥♠")
        self.root.geometry("950x900")
        self.root.resizable(False, False)

        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=6)
        self.root.rowconfigure(2, weight=4)
        self.root.columnconfigure(0, weight=1)

        self.server_url = "http://localhost:5000"
        self.player_name = "Player"
        self.room_id = None
        self.player_id = None
        
        self.is_cpu_mode = False
        self.local_room = None
        
        self.chip_flow_text = "モード選択待ち..."
        self.state_data = {}

        self.setup_ui()
        self.prompt_mode_selection()

    def prompt_mode_selection(self):
        # モード選択の確認
        mode_choice = messagebox.askyesnocancel("モード選択", "オンライン対人戦をプレイしますか？\n\n【はい】 -> 対人戦\n【いいえ】 -> CPU戦\n【キャンセル】 -> 終了")
        
        if mode_choice is None:
            self.root.quit()
            sys.exit(0)
            
        name = simpledialog.askstring("名前入力", "あなたの名前を入力してください:", parent=self.root)
        if name: self.player_name = name

        target_p = simpledialog.askinteger("参加人数", "何人プレイにしますか？ (2〜6人):", parent=self.root, minvalue=2, maxvalue=6)
        if not target_p: target_p = 2

        if mode_choice:  # 対人戦モード
            self.is_cpu_mode = False
            url = simpledialog.askstring("接続設定", "RenderのWebサービスURLを入力してください:\n(ローカル検証なら http://localhost:5000)", parent=self.root)
            if url: self.server_url = url.rstrip("/")
            
            try:
                # サーバー側へ目標人数（target_players）も一緒に送るようにHTTPリクエストを少し拡張
                # 今回のserver.pyは既存のassign_roomを叩きます（server側は自動的に引数を受け取ります）
                res = requests.post(f"{self.server_url}/join", json={"name": self.player_name}).json()
                self.room_id = res["room_id"]
                self.player_id = res["player_id"]
                self.chip_flow_text = f"部屋 [{self.room_id}] に入室しました。指定の人数 ({target_p}人) が揃うまでお待ちください..."
                self.poll_server_loop()
            except Exception as e:
                self.chip_flow_text = "❌ サーバーへの接続に失敗しました。"
                self.refresh_table("エラー")
        else:  # CPU戦モード
            self.is_cpu_mode = True
            from controller import OnlinePokerRoom
            self.local_room = OnlinePokerRoom(room_id=999, target_players=target_p)
            self.player_id = self.local_room.add_player(self.player_name, is_human=True)
            
            # 残りの枠をCPUで埋める
            for cpu_idx in range(1, target_p):
                self.local_room.add_player(f"CPU-{cpu_idx}", is_human=False)
                
            self.chip_flow_text = f"ローカルCPU戦を開始しました ({target_p}人プレイ)"
            self.poll_server_loop()

    def setup_ui(self):
        self.top_frame = tk.Frame(self.root, bg="#0d241c", height=45)
        self.top_frame.grid(row=0, column=0, sticky="ew")

        self.announcement_label = tk.Label(self.top_frame, text=self.chip_flow_text, bg="#0d241c", fg="#ffb300", font=("MS Gothic", 11, "bold"))
        self.announcement_label.pack(side="left", padx=10, expand=True)

        self.main_container = tk.Frame(self.root, bg="#1b4d3e")
        self.main_container.grid(row=1, column=0, sticky="nsew")

        self.canvas = tk.Canvas(self.main_container, bg="#1b4d3e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.control_panel = tk.Frame(self.main_container, bg="#123026", bd=3, relief="ridge")

        self.log_frame = tk.Frame(self.root, bg="#0d241c", width=950, height=250)
        self.log_frame.grid(row=2, column=0, sticky="nsew", pady=(2, 0))
        self.log_frame.pack_propagate(False)

        self.scrollbar = tk.Scrollbar(self.log_frame)
        self.scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(self.log_frame, bg="#0d241c", fg="#81c784", font=("Consolas", 11, "bold"), state="disabled", yscrollcommand=self.scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.log_text.yview)

        self.board_popup = BoardPopup(self.root, self)

    def poll_server_loop(self):
        if self.is_cpu_mode:
            # CPU戦ならローカルのルームから状態を即座に引っこ抜く
            res = self.local_room.get_state(self.player_id)
            self.state_data = res
            self.append_log(res.get("action_logs", []))
            self.board_popup.update_chat_logs(res.get("chat_logs", []))
            self.refresh_table(res.get("round_name", ""))
            # CPU戦は同期が早いため少し短めの間隔で更新
            self.root.after(400, self.poll_server_loop)
        else:
            if self.room_id is not None:
                try:
                    res = requests.get(f"{self.server_url}/state", params={"room_id": self.room_id, "player_id": self.player_id}).json()
                    self.state_data = res
                    if res.get("game_started"):
                        self.announcement_label.config(text=f"部屋 [{self.room_id}] オンライン対戦中")
                        self.append_log(res.get("action_logs", []))
                        self.board_popup.update_chat_logs(res.get("chat_logs", []))
                        self.refresh_table(res.get("round_name", ""))
                    else:
                        # まだ始まっていない場合は待機画面を描画
                        self.canvas.delete("all")
                        self.canvas.create_text(475, 220, text=f"⏳ 他のプレイヤーを待っています...\n\n現在の参加人数: {len(res.get('players', []))} 人", fill="white", font=("MS Gothic", 16, "bold"), justify="center")
                except Exception as e:
                    pass
            self.root.after(800, self.poll_server_loop)

    def draw_card_object(self, cx, cy, card_data, is_hidden=False):
        card_w, card_h = 36, 50
        if is_hidden or card_data is None:
            self.canvas.create_rectangle(cx-card_w/2, cy-card_h/2, cx+card_w/2, cy+card_h/2, fill="#b71c1c", outline="white")
            self.canvas.create_text(cx, cy, text="⚡", fill="white", font=("Arial", 14, "bold"))
        else:
            suit, rank = card_data[0], card_data[1]
            color = "red" if suit in ["♥", "♦"] else "black"
            self.canvas.create_rectangle(cx-card_w/2, cy-card_h/2, cx+card_w/2, cy+card_h/2, fill="white", outline="#90a4ae")
            self.canvas.create_text(cx, cy-10, text=suit, fill=color, font=("Arial", 14, "bold"))
            self.canvas.create_text(cx, cy+12, text=rank, fill=color, font=("Arial", 11, "bold"))

    def refresh_table(self, round_name):
        self.canvas.delete("all")
        for widget in self.control_panel.winfo_children(): widget.destroy()
        self.control_panel.place_forget()

        if not self.state_data: return

        width = self.canvas.winfo_width() or 950
        height = self.canvas.winfo_height() or 500
        center_x, center_y = width / 2, height / 2
        rx, ry = 340, 110

        self.canvas.create_oval(center_x-rx, center_y-ry, center_x+rx, center_y+ry, fill="#154234", outline="#0f3025", width=10)
        
        players_data = self.state_data.get("players", [])
        pot_val = sum(p.get("game_bet", 0) for p in players_data)
        self.canvas.create_text(center_x, center_y-45, text=f"【{round_name}】\nTotal Pot: {pot_val} pt", fill="#ffb300", font=("Arial", 12, "bold"), justify="center")

        board = self.state_data.get("board", [])
        if board:
            bx = center_x - (len(board) - 1) * 22
            for idx, card in enumerate(board):
                self.draw_card_object(bx + (idx * 44), center_y, card)

        num_p = len(players_data)
        me = next((p for p in players_data if p["id"] == self.player_id), None)
        
        for i, p in enumerate(players_data):
            angle = math.radians(90 + (i * (360 / num_p)))
            px, py = center_x + rx * math.cos(angle), center_y + ry * math.sin(angle)

            box_color = "#006064" if p["id"] == self.player_id else "#263238"
            if p["is_busted"]: box_color = "#1c1c1c"
            elif p["status"] == "FOLDED": box_color = "#555555"

            self.canvas.create_rectangle(px-72, py-40, px+72, py+40, fill=box_color, outline="white" if p["id"] == self.player_id else "black")
            self.canvas.create_text(px, py-26, text=f"{p['name']}", fill="white", font=("Arial", 10, "bold"))
            self.canvas.create_text(px, py-10, text=f"{p['chips']} pt", fill="#81c784", font=("Arial", 9, "bold"))

            if p["is_busted"]:
                self.canvas.create_text(px, py+15, text="☠️ BUSTED", fill="#ff1744", font=("Arial", 10, "bold"))
            elif p["status"] == "FOLDED":
                self.canvas.create_text(px, py+15, text="🏳️ FOLDED", fill="#b0bec5", font=("Arial", 10, "bold"))
            elif p.get("hand"):
                self.draw_card_object(px-20, py+16, p["hand"][0], False)
                self.draw_card_object(px+20, py+16, p["hand"][1], False)
            else:
                self.draw_card_object(px-20, py+16, None, True)
                self.draw_card_object(px+20, py+16, None, True)

            if p["round_bet"] > 0 and not p["is_busted"]:
                self.canvas.create_text(px, py+50, text=f"Bet: {p['round_bet']}pt", fill="#ffab91", font=("Arial", 9, "italic"))

        if self.state_data.get("current_turn_player_id") == self.player_id and me and me["status"] == "PLAYING":
            self.draw_action_ui(width, height, me)

        if self.state_data.get("show_intermission"):
            self.draw_intermission_ui(width, height)

    def draw_action_ui(self, width, height, me):
        self.control_panel.place(x=width/2 - 240, y=height - 110, width=480, height=100)
        tk.Label(self.control_panel, text=f"【あなたの番】所持: {me['chips']}pt", bg="#123026", fg="#ffff00", font=("Arial", 9, "bold")).pack(pady=2)

        btn_frame = tk.Frame(self.control_panel, bg="#123026")
        btn_frame.pack(fill="x", padx=10, pady=2)

        tk.Button(btn_frame, text="フォールド", bg="#cfd8dc", width=10, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_action("fold", 0)).pack(side="left", padx=5)
        
        highest_bet = self.state_data.get("highest_bet", 0)
        to_call = min(highest_bet - me["round_bet"], me["chips"])
        c_text = "チェック" if to_call == 0 else f"{to_call}pt コール"
        tk.Button(btn_frame, text=c_text, bg="#a5d6a7", width=14, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_action("call", to_call)).pack(side="left", padx=5)

        min_in = (highest_bet + self.state_data.get("min_raise_increment", 20)) - me["round_bet"]
        max_in = me["chips"]
        
        if max_in >= min_in:
            r_text = "ベット" if highest_bet == 0 else "レイズ"
            self.raise_amount_var = tk.IntVar(value=min_in)
            tk.Button(btn_frame, text=r_text, bg="#ffab91", width=8, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_action("raise", self.raise_amount_var.get())).pack(side="left", padx=5)
            tk.Scale(btn_frame, from_=min_in, to=max_in, orient="horizontal", variable=self.raise_amount_var, bg="#123026", fg="white", highlightthickness=0, length=120).pack(side="left", padx=5)

    def submit_action(self, act_type, amount):
        if self.is_cpu_mode:
            self.local_room.handle_action(self.player_id, act_type, amount)
        else:
            try:
                requests.post(f"{self.server_url}/action", json={
                    "room_id": self.room_id,
                    "player_id": self.player_id,
                    "act_type": act_type,
                    "amount": amount
                })
            except:
                pass

    def draw_intermission_ui(self, width, height):
        self.control_panel.place(x=width/2 - 160, y=height/2 - 50, width=320, height=100)
        tk.Label(self.control_panel, text="ゲームを続けますか？", bg="#123026", fg="white", font=("MS Gothic", 11, "bold")).pack(pady=10)
        f = tk.Frame(self.control_panel, bg="#123026")
        f.pack()
        tk.Button(f, text="次戦へ進む", bg="#a5d6a7", width=12, font=("MS Gothic", 9, "bold"), command=self.submit_intermission).pack(side="left", padx=10)

    def submit_intermission(self):
        if self.is_cpu_mode:
            if self.local_room.show_intermission:
                self.local_room.start_new_game()
        else:
            try:
                requests.post(f"{self.server_url}/intermission", json={"room_id": self.room_id})
            except:
                pass

    def append_log(self, messages):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        for msg in messages:
            self.log_text.insert(tk.END, f" {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = TexasHoldemGUI(root)
    root.mainloop()
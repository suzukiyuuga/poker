import math
import sys
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import requests

from action_popup import ActionPopup


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

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.label = tk.Label(self.window, text="💬 リアルタイムチャット掲示板", font=("Arial", 11, "bold"), pady=10)
        self.label.pack(side=tk.TOP, fill=tk.X)
        
        # 1. 下部の入力フレームを先に配置して領域を固定・確保
        input_frame = tk.Frame(self.window)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.send_btn = tk.Button(input_frame, text="送信", command=self.send_message, bg="#4caf50", fg="white", font=("Arial", 9, "bold"))
        self.send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # 入力ボックスを明示的に state=tk.NORMAL で生成
        self.entry = tk.Entry(input_frame, font=("MS Gothic", 10), state=tk.NORMAL)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda event: self.send_message())
        
        # 2. ログ表示エリアを真ん中の残りの領域に配置
        self.text_area = scrolledtext.ScrolledText(self.window, wrap=tk.WORD, width=40, height=22, font=("MS Gothic", 10), bg="#f4f6f9", fg="#2c3e50")
        self.text_area.pack(side=tk.TOP, padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.config(state=tk.DISABLED)

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
                if msg.startswith("/advice"):
                    self.client.get_local_ai_advice(msg)
                else:
                    self.client.local_room.chat_logs.append(f"【{self.client.player_name}】: {msg}")
                self.entry.delete(0, tk.END)
            else:
                try:
                    requests.post(f"{self.client.server_url}/chat", json={
                        "room_id": self.client.room_id,
                        "player_id": self.client.player_id,
                        "name": self.client.player_name,
                        "message": msg
                    })
                    self.entry.delete(0, tk.END)
                except:
                    pass

    def on_closing(self):
        messagebox.showwarning(
            "操作無効", 
            "ゲーム進行に影響が出るため、チャット掲示板を閉じることはできません！\nそのまま表示してお使いください。",
            parent=self.window
        )

class TexasHoldemGUI:
    def open_action_popup(self, me):
        if hasattr(self, "action_popup_open") and self.action_popup_open:
            return

        self.action_popup_open = True

        highest_bet = self.state_data.get("highest_bet", 0)
        min_raise_inc = self.state_data.get("min_raise_increment", 20)
        to_call = min(highest_bet - me["round_bet"], me["chips"])
        can_raise = me["chips"] > to_call

        popup = ActionPopup(self.root, me, to_call, can_raise, min_raise_inc=min_raise_inc)
        
        try:
            popup.grab_release()
        except Exception:
            pass

        # ★ wait_window を使わず、ポップアップ閉鎖時に呼び出すコールバックを設定
        def on_popup_close():
            self.action_popup_open = False
            if popup.result_action:
                self.submit_action(popup.result_action, popup.result_amount)

        # ポップアップ破棄時にコールバックを実行（wait_windowでブロックしないため poll_server_loop が動きます）
        popup.bind("<Destroy>", lambda e: on_popup_close() if e.widget == popup else None)

    def __init__(self, root):
        self.root = root
        self.root.title("♠♥♦♣ テキサスホールデム・ポーカー ♣♦♥♠")
        self.root.geometry("950x750")
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
        self.target_players = 2

        self.pending_cpu_turn_id = None

        self.control_panel_mode = None
        self.rendered_action_log_count = 0
        self.rendered_chat_log_count = 0
        self.last_round_name = None

        self.setup_ui()
        self.prompt_mode_selection()

    def get_local_ai_advice(self, msg):
        import os
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            self.local_room.send_private_message(self.player_id, "💡 【AI助言】環境変数 OPENAI_API_KEY が設定されていないため助言機能を利用できません。")
            return
        
        prompt_text = self.local_room.get_advice_prompt(self.player_id, msg)
        try:
            res = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "あなたはテキサスホールデム・ポーカーのアドバイザーです。テキサスホールデムポーカーのルールは、手札2枚とゲームが進むごとに公開される最大5枚の場のカードの合わせて7枚のカードから5枚のカードを選び、より強い役を作るというものです。役は強い順にロイヤルストレートフラッシュ、ストレートフラッシュ、4カード、フルハウス、フラッシュ、ストレート、3カード、ツーペア、ワンペア、ノーペアです。本来のテキサスホールデムポーカーはA~Kまでのカードを用いますがこのルールでは毎ゲームで0~87の乱数が足された連続13種のカードを用います。プレイヤーの状況(自分の手札、場札、チップ量)のみを元に、短く的確にアドバイスしてください。"},
                        {"role": "user", "content": prompt_text}
                    ],
                    "max_tokens": 150
                },
                timeout=10
            )
            if res.status_code == 200:
                advice = res.json()["choices"][0]["message"]["content"].strip()
                advice_msg = f"💡 【AI助言】\n{advice}"
            else:
                advice_msg = f"💡 【AI助言エラー】APIからの応答に失敗しました。(Status: {res.status_code})"
        except Exception as e:
            advice_msg = f"💡 【AI助言エラー】通信エラーが発生しました: {e}"

        self.local_room.send_private_message(self.player_id, advice_msg)

    def prompt_mode_selection(self):
        mode_choice = messagebox.askyesnocancel("モード選択", "オンライン対人戦をプレイしますか？\n\n【はい】 -> 対人戦\n【いいえ】 -> CPU戦\n【キャンセル】 -> 終了")
        
        if mode_choice is None:
            self.root.quit()
            sys.exit(0)
            
        name = simpledialog.askstring("名前入力", "あなたの名前を入力してください:", parent=self.root)
        if name: self.player_name = name

        if mode_choice:
            self.is_cpu_mode = False
            url = simpledialog.askstring("接続設定", "RenderのWebサービスURLを入力してください:\n(ローカル検証なら http://localhost:5000)", parent=self.root)
            if url: self.server_url = url.rstrip("/")
            
            try:
                res = requests.post(f"{self.server_url}/join", json={
                    "name": self.player_name
                }).json()
                
                self.room_id = res["room_id"]
                self.player_id = res["player_id"]
                is_host = res.get("is_host", False)

                if is_host:
                    target_p = simpledialog.askinteger("参加人数設定", "部屋のホストになりました！\n何人プレイにしますか？ (2〜6人):", parent=self.root, minvalue=2, maxvalue=6)
                    if not target_p: target_p = 2
                    self.target_players = target_p
                    
                    requests.post(f"{self.server_url}/setup_room", json={
                        "room_id": self.room_id,
                        "target_players": self.target_players
                    })
                else:
                    self.target_players = res.get("target_players", 2)
                    
                self.chip_flow_text = f"部屋 [{self.room_id}] に入室しました。指定の人数 ({self.target_players}人) が揃うまでお待ちください..."
                self.poll_server_loop()
            except Exception as e:
                self.chip_flow_text = "❌ サーバーへの接続に失敗しました。"
                self.refresh_table("エラー")
        else:
            self.is_cpu_mode = True
            
            target_p = simpledialog.askinteger("参加人数", "何人プレイにしますか？ (2〜6人):", parent=self.root, minvalue=2, maxvalue=6)
            if not target_p: target_p = 2
            self.target_players = target_p
            
            from controller import OnlinePokerRoom
            self.local_room = OnlinePokerRoom(room_id=999, target_players=target_p)
            self.player_id = self.local_room.add_player(self.player_name, is_human=True)
            
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

        # 下部に余白(pady)を追加し、最下行のログが画面下部で見切れないように修正
        self.log_frame = tk.Frame(self.root, bg="#0d241c", width=950, height=160)
        self.log_frame.grid(row=2, column=0, sticky="nsew", pady=(2, 20), padx=5)
        self.log_frame.pack_propagate(False)

        self.scrollbar = tk.Scrollbar(self.log_frame)
        self.scrollbar.pack(side="right", fill="y")

        # ★ 修正: state="disabled" を解除し、キー入力を拒否することでスクロールを常時有効化
        self.log_text = tk.Text(self.log_frame, bg="#0d241c", fg="#81c784", font=("Consolas", 11, "bold"), yscrollcommand=self.scrollbar.set)
        self.log_text.bind("<Key>", lambda e: "break")
        self.log_text.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.log_text.yview)

        self.board_popup = BoardPopup(self.root, self)

    def poll_server_loop(self):
        if self.is_cpu_mode:
            res = self.local_room.get_state(self.player_id)
            self.state_data = res
            self.append_log(res.get("action_logs", []))
            self.board_popup.update_chat_logs(res.get("chat_logs", []))
            self.refresh_table(res.get("round_name", ""))
            
            self.schedule_cpu_action_if_needed()
            self.root.after(400, self.poll_server_loop)
        else:
            if self.room_id is not None:
                try:
                    res = requests.get(f"{self.server_url}/state", params={"room_id": self.room_id, "player_id": self.player_id}).json()
                    self.state_data = res
                    self.target_players = res.get("target_players", self.target_players)
                    
                    if res.get("game_started"):
                        self.announcement_label.config(text=f"部屋 [{self.room_id}] オンライン対戦中")
                        self.append_log(res.get("action_logs", []))
                        self.board_popup.update_chat_logs(res.get("chat_logs", []))
                        self.refresh_table(res.get("round_name", ""))
                    else:
                        current_p_count = len(res.get('players', []))
                        self.canvas.delete("all")
                        self.canvas.create_text(
                            475, 220, 
                            text=f"⏳ 他のプレイヤーを待っています...\n\n現在の参加人数: {current_p_count} / {self.target_players} 人", 
                            fill="white", font=("MS Gothic", 16, "bold"), justify="center"
                        )
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

        if not self.state_data:
            return

        players_data = self.state_data.get("players", [])
        me = next((p for p in players_data if p["id"] == self.player_id), None)

        is_my_turn = (
            self.state_data.get("current_turn_player_id") == self.player_id
            and me
            and me["status"] == "PLAYING"
        )
        is_intermission = self.state_data.get("show_intermission", False)

        if is_intermission:
            desired_mode = "intermission"
        elif is_my_turn:
            desired_mode = "action"
        else:
            desired_mode = None        

        width = self.canvas.winfo_width() or 950
        height = self.canvas.winfo_height() or 500
        center_x, center_y = width / 2, height / 2 - 35
        rx, ry = 340, 110

        self.canvas.create_oval(center_x-rx, center_y-ry, center_x+rx, center_y+ry, fill="#154234", outline="#0f3025", width=10)
        
        pot_val = sum(p.get("game_bet", 0) for p in players_data)
        self.canvas.create_text(center_x, center_y-45, text=f"【{round_name}】\nTotal Pot: {pot_val} pt", fill="#ffb300", font=("Arial", 12, "bold"), justify="center")

        board = self.state_data.get("board", [])
        if board:
            bx = center_x - (len(board) - 1) * 22
            for idx, card in enumerate(board):
                self.draw_card_object(bx + (idx * 44), center_y, card)

        num_p = len(players_data)
        
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

        if desired_mode != self.control_panel_mode:
            for widget in self.control_panel.winfo_children():
                widget.destroy()
            self.control_panel.place_forget()
            self.control_panel_mode = desired_mode
            
            if desired_mode == "intermission":
                self.draw_intermission_ui(width, height)
        else:
            if desired_mode == "intermission":
                self.control_panel.place(x=width/2 - 160, y=height - 80, width=320, height=70)
            else:
                self.control_panel.place_forget()

        if desired_mode == "action":
            self.open_action_popup(me)

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
        self.control_panel.place(x=width/2 - 160, y=height - 80, width=320, height=70)
        tk.Label(self.control_panel, text="ゲームを続けますか？", bg="#123026", fg="white", font=("MS Gothic", 11, "bold")).pack(pady=10)
        f = tk.Frame(self.control_panel, bg="#123026")
        f.pack()
        tk.Button(f, text="次戦へ進む", bg="#a5d6a7", width=12, font=("MS Gothic", 9, "bold"), command=self.submit_intermission).pack(side="left", padx=10)

    def submit_intermission(self):
        # ★ 修正: state 切り替えなしで消去
        self.log_text.delete("1.0", tk.END)

        if self.is_cpu_mode:
            if self.local_room.show_intermission:
                self.local_room.start_new_game()
        else:
            try:
                requests.post(f"{self.server_url}/intermission", json={"room_id": self.room_id})
            except:
                pass

    def append_log(self, messages):
        # action_logs が前回より短くなっていたら（新ゲーム開始時など）、GUI側もリセット
        if len(messages) < self.rendered_action_log_count:
            self.log_text.delete("1.0", tk.END)
            self.rendered_action_log_count = 0
        
        # messages 全体のうち、まだ描画していないぶんだけ抽出
        new_messages = messages[self.rendered_action_log_count:]
        if not new_messages:
            return

        # ★ 修正: state 切り替えなしで挿入
        for msg in new_messages:
            self.log_text.insert(tk.END, f" {msg}\n")
        
        # 確実に最下部までスクロール（update_idletasksで描画を反映させてからスクロール）
        self.log_text.update_idletasks()
        self.log_text.see(tk.END)

        self.rendered_action_log_count = len(messages)

    def schedule_cpu_action_if_needed(self):
        if not self.is_cpu_mode or not self.local_room or not self.state_data or self.state_data.get("show_intermission", False):
            return

        current_id = self.state_data.get("current_turn_player_id")
        if current_id is None:
            self.pending_cpu_turn_id = None
            return

        player = next((p for p in self.local_room.players if p.id == current_id), None)
        if player is None or player.is_human or self.pending_cpu_turn_id == current_id:
            return

        self.pending_cpu_turn_id = current_id
        self.root.after(900, lambda pid=current_id: self.execute_cpu_action(pid))
        
    def execute_cpu_action(self, player_id):
        if self.pending_cpu_turn_id != player_id or not self.local_room or self.local_room.current_turn_player_id != player_id:
            self.pending_cpu_turn_id = None
            return

        cpu_player = next((p for p in self.local_room.players if p.id == player_id), None)
        if cpu_player is None or cpu_player.is_human:
            self.pending_cpu_turn_id = None
            return

        self.pending_cpu_turn_id = None
        self.local_room.think_cpu_action(cpu_player)


if __name__ == "__main__":
    root = tk.Tk()
    app = TexasHoldemGUI(root)
    
    def on_closing():
        if not app.is_cpu_mode and app.room_id is not None and app.player_id is not None:
            try:
                requests.post(f"{app.server_url}/leave", json={
                    "room_id": app.room_id,
                    "player_id": app.player_id
                }, timeout=1.0)
            except:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
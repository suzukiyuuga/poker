import math
import sys
import threading
import time
import tkinter as tk

# 提供されたゲームロジックファイルをインポート
from super_main import HandStatus, Player, TexasHoldemGame


class ResetGameException(Exception):
    """ゲームを安全に終了させるための例外"""
    pass


class GuardedList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_append = False

    def append(self, item):
        if self.block_append:
            return
        list.append(self, item)


class TexasHoldemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("♠♥♦♣ テキサスホールデム・ポーカー ♣♦♥♠")
        self.root.geometry("950x900")
        self.root.resizable(False, False)

        # 画面の3分割レイアウト設定
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=6)
        self.root.rowconfigure(2, weight=4)
        self.root.columnconfigure(0, weight=1)

        # 状態管理変数
        self.game = None
        self.game_thread = None
        self.is_game_over = False
        
        self.action_event = threading.Event()
        self.selected_action = (None, 0)
        
        # UI制御フラグ
        self.show_setup_panel = True
        self.setup_step = "players"
        self.show_action_panel = False
        self.show_intermission_panel = False
        self.show_loading_delay = False
        
        self.num_players = 3
        self.debug_mode = False
        self.chip_flow_text = "初期設定を行ってください"

        self.setup_ui()
        
        # 0.1秒ごとにプレイヤーの状態やスレッド生存を監視するメインタイマー
        self.game_monitor_loop()

    def setup_ui(self):
        # 1. 最上部ヘッダー
        self.top_frame = tk.Frame(self.root, bg="#0d241c", height=45)
        self.top_frame.grid(row=0, column=0, sticky="ew")

        self.btn_title = tk.Button(
            self.top_frame, text="タイトルへ戻る", bg="#c62828", fg="white",
            font=("MS Gothic", 10, "bold"), command=self.return_to_title
        )
        self.btn_title.pack(side="left", padx=15, pady=8)

        self.announcement_label = tk.Label(
            self.top_frame, text=self.chip_flow_text, bg="#0d241c", fg="#ffb300",
            font=("MS Gothic", 11, "bold")
        )
        self.announcement_label.pack(side="left", padx=10, expand=True)

        # 2. メイン対戦キャンバス
        self.main_container = tk.Frame(self.root, bg="#1b4d3e")
        self.main_container.grid(row=1, column=0, sticky="nsew")

        self.canvas = tk.Canvas(self.main_container, bg="#1b4d3e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.control_panel = tk.Frame(self.main_container, bg="#123026", bd=3, relief="ridge")

        # 3. 下部ログエリア（レイアウト崩れ対策版）
        self.log_frame = tk.Frame(self.root, bg="#0d241c", width=950, height=350)
        self.log_frame.grid(row=2, column=0, sticky="nsew", pady=(2, 0))
        self.log_frame.pack_propagate(False)

        self.scrollbar = tk.Scrollbar(self.log_frame)
        self.scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            self.log_frame, bg="#0d241c", fg="#81c784",
            font=("Consolas", 11, "bold"), state="disabled",
            yscrollcommand=self.scrollbar.set
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.log_text.yview)

        self.refresh_table("初期設定")

    def game_monitor_loop(self):
        """裏ロジックの状態変化や、突然の終了を検知する心臓部"""
        if self.game and not self.is_game_over:
            human = next((p for p in self.game.players if p.is_human), None)
            
            # パターンA: チップが0になった瞬間（ログ出力やインターミッション中）
            if human and (human.chips <= 0 or human.is_busted):
                if any("wins" in log or "獲得" in log or "破産" in log for log in self.game.action_logs) or self.show_intermission_panel:
                    self.process_game_over_trigger()
                    return

            # パターンB: 裏のゲームスレッドが終了したのにゲームオーバーになっていない場合（強制回収）
            if self.game_thread and not self.game_thread.is_alive():
                if human and (human.chips <= 0 or human.is_busted):
                    self.process_game_over_trigger()
                    return
                    
        self.root.after(100, self.game_monitor_loop)

    def process_game_over_trigger(self):
        self.is_game_over = True
        self.show_action_panel = False
        self.show_intermission_panel = False
        self.show_loading_delay = False
        self.chip_flow_text = "❌ 破産しました。ゲームオーバーです。"
        self.action_event.set()
        self.refresh_table("ゲームオーバー")

    def return_to_title(self):
        self.is_game_over = True
        self.action_event.set()

        self.show_setup_panel = True
        self.setup_step = "players"
        self.show_action_panel = False
        self.show_intermission_panel = False
        self.show_loading_delay = False
        self.chip_flow_text = "初期設定を行ってください"
        
        self.game = None
        self.game_thread = None
        
        self.refresh_table("初期設定")

    def start_game_flow(self):
        self.is_game_over = False
        self.show_setup_panel = False
        
        self.game = TexasHoldemGame()
        self.game.players = GuardedList()
        self.game.debug_mode = self.debug_mode

        self.game.safe_input = self.gui_safe_input
        self.game.draw_ui = self.gui_draw_ui
        self.game.handle_human_action = self.gui_handle_human_action

        self.game_thread = threading.Thread(target=self.start_poker_logic, daemon=True)
        self.game_thread.start()

    def check_abort(self):
        if self.is_game_over or self.game is None:
            raise ResetGameException()

    def start_poker_logic(self):
        try:
            self.check_abort()
            self.game.players.append(Player(0, "あなた", chips=1000, is_human=True))
            for i in range(1, self.num_players):
                self.game.players.append(Player(i, f"CPU {i}", chips=1000, is_human=False))
            self.game.players.block_append = True
            
            self.game.start_game_loop()
        except ResetGameException:
            return
        except Exception as e:
            if not self.is_game_over:
                print(f"Logic Error: {e}")

    def gui_safe_input(self, prompt):
        self.check_abort()
        if "プレイ人数" in prompt: return str(self.num_players)
        if "デバッグモード" in prompt: return "y" if self.debug_mode else "n"

        if "Enter" in prompt or "次" in prompt:
            self.inject_final_results_to_log()
            
            # 勝者ログの抽出
            for log in reversed(self.game.action_logs):
                if any(x in log for x in ["wins", "獲得", "勝者"]):
                    self.chip_flow_text = f"💰 {log.strip()}"
                    break
            
            self.check_abort()
            
            # 自分がトビていたらボタン入力を待たずに即時ゲームオーバーへ誘導
            human = next((p for p in self.game.players if p.is_human), None) if self.game else None
            if human and (human.chips <= 0 or human.is_busted):
                self.process_game_over_trigger()
                raise ResetGameException()

            # 自分がフォールドしているなら「次戦へ進む」ボタン待ちを完全スルー
            if human and human.status == HandStatus.FOLDED:
                return ""  
            
            # 生存している時だけボタン入力を待つ
            self.show_intermission_panel = True
            self.intermission_response = ""
            self.root.after(0, self.refresh_table, "ディール終了")

            self.action_event.clear()
            self.action_event.wait()
            self.check_abort()

            self.show_intermission_panel = False
            self.chip_flow_text = "新しいゲームの準備中..."
            return self.intermission_response

        return ""

    def inject_final_results_to_log(self):
        if not self.game: return
        if any("最終結果" in log for log in self.game.action_logs): return

        self.game.action_logs.append("================= 最終結果 (Showdown) =================")
        for p in self.game.players:
            if p.is_busted:
                self.game.action_logs.append(f" • {p.name}: 破産退場済")
            elif p.status == HandStatus.FOLDED:
                self.game.action_logs.append(f" • {p.name}: フォールド済")
            else:
                h_name = p.hand_name if (hasattr(p, 'hand_name') and p.hand_name) else "ハイカード"
                self.game.action_logs.append(f" • {p.name} [{p.hand[0]} {p.hand[1]}] => 【{h_name}】")
        self.game.action_logs.append("========================================================")
        
        human = next((p for p in self.game.players if p.is_human), None) if self.game else None
        if not (human and human.status == HandStatus.FOLDED):
            self.root.after(0, self.refresh_table, "結果発表")

    def gui_draw_ui(self, round_name):
        self.check_abort()
        human = next((p for p in self.game.players if p.is_human), None) if self.game else None
        
        if human:
            if human.status == HandStatus.FOLDED:
                return
            
            if human.chips == 0 and not self.is_game_over:
                self.root.after(0, self.refresh_table, round_name)
                time.sleep(2.0)
                return

        self.root.after(0, self.refresh_table, round_name)
        time.sleep(0.4)

    def gui_handle_human_action(self, p, to_call, highest_bet, min_raise_increment, can_raise):
        self.check_abort()
        
        self.current_player_obj = p
        self.current_to_call = min(to_call, p.chips)
        self.min_raise_inc = min_raise_increment
        self.highest_bet = highest_bet
        self.can_raise = can_raise

        if highest_bet > 0:
            self.chip_flow_text = f"📢 基準ベット: {highest_bet}pt (あなたのコール額: {self.current_to_call}pt)"
        else:
            self.chip_flow_text = "📢 ベットはありません。チェック可能です。"

        self.show_action_panel = True
        self.root.after(0, self.refresh_table, "あなたのターン")

        self.action_event.clear()
        self.action_event.wait()
        
        self.check_abort()
        self.show_action_panel = False
        return self.selected_action

    def draw_card_object(self, cx, cy, card_obj, is_hidden=False):
        card_w, card_h = 36, 50
        if is_hidden:
            self.canvas.create_rectangle(cx-card_w/2, cy-card_h/2, cx+card_w/2, cy+card_h/2, fill="#b71c1c", outline="white")
            self.canvas.create_text(cx, cy, text="⚡", fill="white", font=("Arial", 14, "bold"))
        else:
            suit = getattr(card_obj, 'suit', str(card_obj)[0])
            rank = getattr(card_obj, 'rank', str(card_obj)[1:])
            color = "red" if suit in ["♥", "♦"] else "black"
            self.canvas.create_rectangle(cx-card_w/2, cy-card_h/2, cx+card_w/2, cy+card_h/2, fill="white", outline="#90a4ae")
            self.canvas.create_text(cx, cy-10, text=suit, fill=color, font=("Arial", 14, "bold"))
            self.canvas.create_text(cx, cy+12, text=rank, fill=color, font=("Arial", 11, "bold"))

    def refresh_table(self, round_name):
        self.canvas.delete("all")
        
        for widget in self.control_panel.winfo_children():
            widget.destroy()
        self.control_panel.place_forget()

        if self.show_setup_panel:
            self.draw_setup_ui()
            return

        # メインテーブル描画
        width = self.canvas.winfo_width() or 950
        height = self.canvas.winfo_height() or 500
        center_x, center_y = width / 2, height / 2
        rx, ry = 340, 110

        self.canvas.create_oval(center_x-rx, center_y-ry, center_x+rx, center_y+ry, fill="#154234", outline="#0f3025", width=10)
        
        pot_val = sum(p.game_bet for p in self.game.players) if self.game else 0
        self.canvas.create_text(center_x, center_y-45, text=f"【{round_name}】\nTotal Pot: {pot_val} pt", fill="#ffb300", font=("Arial", 12, "bold"), justify="center")

        if self.game and self.game.board:
            bx = center_x - (len(self.game.board) - 1) * 22
            for idx, card in enumerate(self.game.board):
                self.draw_card_object(bx + (idx * 44), center_y, card)

        if self.game:
            num_p = len(self.game.players)
            is_showdown = "結果発表" in round_name or self.is_game_over
            for i, p in enumerate(self.game.players):
                angle = math.radians(90 + (i * (360 / num_p)))
                px, py = center_x + rx * math.cos(angle), center_y + ry * math.sin(angle)

                box_color = "#006064" if p.is_human else "#263238"
                if p.is_busted: box_color = "#1c1c1c"
                elif p.status == HandStatus.FOLDED: box_color = "#555555"

                self.canvas.create_rectangle(px-72, py-40, px+72, py+40, fill=box_color, outline="white" if p.is_human else "black")
                self.canvas.create_text(px, py-26, text=f"{p.name}{' [D]' if i==self.game.dealer_idx else ''}", fill="white", font=("Arial", 10, "bold"))
                self.canvas.create_text(px, py-10, text=f"{p.chips} pt", fill="#81c784", font=("Arial", 9, "bold"))

                if p.is_busted:
                    self.canvas.create_text(px, py+15, text="☠️ BUSTED", fill="#ff1744", font=("Arial", 10, "bold"))
                elif p.status == HandStatus.FOLDED:
                    self.canvas.create_text(px, py+15, text="🏳️ FOLDED", fill="#b0bec5", font=("Arial", 10, "bold"))
                elif len(p.hand) == 2:
                    visible = p.is_human or self.debug_mode or is_showdown
                    self.draw_card_object(px-20, py+16, p.hand[0], not visible)
                    self.draw_card_object(px+20, py+16, p.hand[1], not visible)

                if p.round_bet > 0 and not p.is_busted:
                    self.canvas.create_text(px, py+50, text=f"Bet: {p.round_bet}pt", fill="#ffab91", font=("Arial", 9, "italic"))

        # 行動選択パネル
        if self.show_action_panel and not self.is_game_over and not self.show_loading_delay:
            self.draw_action_ui(width, height)

        # 思考中パネル
        if self.show_loading_delay and not self.is_game_over:
            self.control_panel.place(x=width/2 - 120, y=height - 90, width=240, height=60)
            tk.Label(self.control_panel, text="思考中 / ディール中...", bg="#123026", fg="#ffb300", font=("MS Gothic", 11, "bold")).pack(pady=15)

        # ディール終了パネル
        if self.show_intermission_panel and not self.is_game_over and not self.show_loading_delay:
            self.draw_intermission_ui(width, height)

        # ゲームオーバー時のリベンジパネル
        if self.is_game_over:
            self.canvas.create_rectangle(center_x-280, center_y-75, center_x+280, center_y+75, fill="#1a0c0c", outline="#ff1744", width=4)
            self.canvas.create_text(center_x, center_y-20, text="💸 BANKRUPT 💸", fill="#ff1744", font=("Impact", 38, "bold"))
            self.canvas.create_text(center_x, center_y+20, text="所持チップがゼロになりました。", fill="white", font=("MS Gothic", 12, "bold"))
            
            tk.Button(
                self.control_panel, text="もう一度挑戦する (リベンジ)", bg="#ffb300", fg="black",
                font=("MS Gothic", 11, "bold"), width=26, height=2, command=self.return_to_title
            ).pack(pady=10)
            self.control_panel.place(x=center_x-130, y=center_y+95, width=260, height=60)

        if self.game:
            self.append_log(self.game.action_logs)

    def draw_setup_ui(self):
        self.announcement_label.config(text="初期設定画面")
        cx, cy = 475, 220
        self.canvas.create_rectangle(cx-200, cy-120, cx+200, cy+150, fill="#0d241c", outline="#ffb300", width=2)
        
        if self.setup_step == "players":
            self.canvas.create_text(cx, cy-70, text="★ プレイ人数を選択 ★", fill="white", font=("MS Gothic", 14, "bold"))
            self.control_panel.place(x=cx-150, y=cy-20, width=300, height=130)
            
            tk.Label(self.control_panel, text="何人でプレイしますか？", bg="#123026", fg="white", font=("MS Gothic", 10)).pack(pady=10)
            frame_btns = tk.Frame(self.control_panel, bg="#123026")
            frame_btns.pack(pady=5)
            for n in range(2, 7):
                tk.Button(frame_btns, text=f"{n}人", width=4, font=("Arial", 10, "bold"), command=lambda num=n: self.set_setup_players(num)).pack(side="left", padx=4)
                
        elif self.setup_step == "debug":
            self.canvas.create_text(cx, cy-70, text="★ モード選択 ★", fill="white", font=("MS Gothic", 14, "bold"))
            self.control_panel.place(x=cx-150, y=cy-20, width=300, height=130)
            
            tk.Label(self.control_panel, text="デバッグモードにしますか？\n(CPUの手札が常に見えるようになります)", bg="#123026", fg="white", font=("MS Gothic", 10), justify="center").pack(pady=12)
            frame_btns = tk.Frame(self.control_panel, bg="#123026")
            frame_btns.pack(pady=2)
            tk.Button(frame_btns, text="はい (手札表示)", width=12, bg="#ffab91", font=("MS Gothic", 9, "bold"), command=lambda: self.set_setup_debug(True)).pack(side="left", padx=10)
            tk.Button(frame_btns, text="いいえ (通常)", width=12, bg="#a5d6a7", font=("MS Gothic", 9, "bold"), command=lambda: self.set_setup_debug(False)).pack(side="left", padx=10)

    def draw_action_ui(self, width, height):
        self.control_panel.place(x=width/2 - 240, y=height - 110, width=480, height=100)
        p = self.current_player_obj
        tk.Label(self.control_panel, text=f"【あなたの番】所持: {p.chips}pt / 既ベット: {p.round_bet}pt", bg="#123026", fg="#ffff00", font=("Arial", 9, "bold")).pack(pady=2)

        btn_frame = tk.Frame(self.control_panel, bg="#123026")
        btn_frame.pack(fill="x", padx=10, pady=2)

        tk.Button(btn_frame, text="フォールド", bg="#cfd8dc", width=10, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_action("fold", 0)).pack(side="left", padx=5)
        
        c_text = "チェック" if self.current_to_call == 0 else f"{self.current_to_call}pt コール"
        tk.Button(btn_frame, text=c_text, bg="#a5d6a7", width=14, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_action("call", self.current_to_call)).pack(side="left", padx=5)

        min_in = (self.highest_bet + self.min_raise_inc) - p.round_bet
        max_in = p.chips
        
        if self.can_raise and max_in >= min_in:
            r_text = "ベット" if self.highest_bet == 0 else "レイズ"
            self.raise_amount_var = tk.IntVar(value=min_in)
            
            tk.Button(btn_frame, text=r_text, bg="#ffab91", width=8, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_action("raise", self.raise_amount_var.get())).pack(side="left", padx=5)
            tk.Scale(btn_frame, from_=min_in, to=max_in, orient="horizontal", variable=self.raise_amount_var, bg="#123026", fg="white", highlightthickness=0, length=120).pack(side="left", padx=5)
        else:
            tk.Button(btn_frame, text="レイズ不可", state="disabled", width=12, font=("MS Gothic", 9)).pack(side="left", padx=5)

    def set_setup_players(self, num):
        self.num_players = num
        self.setup_step = "debug"
        self.refresh_table("初期設定")

    def set_setup_debug(self, mode):
        self.debug_mode = mode
        self.setup_step = "none"
        self.start_game_flow()

    def submit_action(self, act_type, amount):
        self.selected_action = (act_type, amount)
        if act_type == "fold":
            self.show_loading_delay = False
            self.action_event.set()
        else:
            self.show_loading_delay = True
            self.refresh_table("対戦中")
            self.root.after(400, self.release_action_lock)

    def release_action_lock(self):
        self.show_loading_delay = False
        self.action_event.set()

    def draw_intermission_ui(self, width, height):
        self.control_panel.place(x=width/2 - 160, y=height/2 - 50, width=320, height=100)
        tk.Label(self.control_panel, text="ゲームを続けますか？", bg="#123026", fg="white", font=("MS Gothic", 11, "bold")).pack(pady=10)
        
        f = tk.Frame(self.control_panel, bg="#123026")
        f.pack()
        tk.Button(f, text="次戦へ進む", bg="#a5d6a7", width=12, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_intermission("")).pack(side="left", padx=10)
        tk.Button(f, text="終了する", bg="#cfd8dc", width=12, font=("MS Gothic", 9, "bold"), command=lambda: self.submit_intermission("exit")).pack(side="left", padx=10)

    def submit_intermission(self, choice):
        if choice == "exit":
            self.root.quit()
            sys.exit(0)
        self.intermission_response = ""
        self.action_event.set()

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
import math
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

# 提供されたゲームロジックファイルをインポート
from super_main import HandStatus, Player, TexasHoldemGame


# 重複追加をブロックするためのカスタムリストクラス
class GuardedList(list):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_append = False

    def append(self, item):
        if self.block_append:
            return
        super().append(item)


class TexasHoldemGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("♠♥♦♣ テキサスホールデム・ポーカー ♣♦♥♠")
        self.root.geometry("950x750")

        # ロジックのインスタンスを作成
        self.game = TexasHoldemGame()
        self.game.players = GuardedList()

        # GUI用の状態管理変数
        self.num_players = 2
        self.debug_mode = False
        self.is_game_over = False

        # GUIとゲームスレッド間の同期用イベント
        self.action_event = threading.Event()
        self.selected_action = (None, 0)

        # 役名・勝者ログの二重出力を防ぐためのフラグ
        self.printed_showdown_log = False

        self.setup_ui()
        self.root.after(100, self.ask_initial_settings)

    def setup_ui(self):
        """画面全体のレイアウト構造を設定"""
        self.canvas = tk.Canvas(self.root, bg="#1b4d3e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # ログの高さを「15行」に拡張
        self.log_text = tk.Text(
            self.root,
            height=15,
            bg="#0d241c",
            fg="#81c784",
            font=("MS Gothic", 10, "bold"),
            state="disabled",
        )
        self.log_text.pack(fill="x", side="bottom")

    def ask_initial_settings(self):
        while True:
            res = simpledialog.askinteger(
                "設定", "プレイ人数を入力してください (2 〜 6人):", minvalue=2, maxvalue=6
            )
            if res:
                self.num_players = res
                break

        self.debug_mode = messagebox.askyesno(
            "設定", "デバッグモード（全員の手札を常時表示）にしますか？"
        )

        self.game.safe_input = self.gui_safe_input
        self.game.draw_ui = self.gui_draw_ui
        self.game.handle_human_action = self.gui_handle_human_action

        self.game_thread = threading.Thread(
            target=self.start_poker_logic, daemon=True
        )
        self.game_thread.start()

    def start_poker_logic(self):
        self.game.debug_mode = self.debug_mode
        self.game.players.append(Player(0, "あなた", chips=1000, is_human=True))
        for i in range(1, self.num_players):
            self.game.players.append(
                Player(i, f"CPU {i}", chips=1000, is_human=False)
            )

        self.game.players.block_append = True

        try:
            self.game.start_game_loop()
        except SystemExit:
            pass

        human_player = next((p for p in self.game.players if p.is_human), None)
        if human_player and human_player.chips <= 0:
            self.inject_final_results_to_log()
            self.is_game_over = True
            self.root.after(0, lambda: self.refresh_table("ゲーム終了"))

    def gui_safe_input(self, prompt):
        if "プレイ人数" in prompt:
            return str(self.num_players)
        if "デバッグモード" in prompt:
            return "y" if self.debug_mode else "n"

        if "Enter" in prompt or "次" in prompt:
            self.inject_final_results_to_log()

            human_player = next((p for p in self.game.players if p.is_human), None)
            if human_player and human_player.chips <= 0:
                self.is_game_over = True
                self.root.after(0, lambda: self.refresh_table("ゲーム終了"))
                while True:
                    time.sleep(1)

            res = messagebox.askyesno(
                "次のゲーム", "次のゲームを開始しますか？（Noで終了）"
            )
            self.printed_showdown_log = False
            if res:
                return ""
            else:
                self.root.quit()
                sys.exit(0)
        return ""

    def inject_final_results_to_log(self):
        """プレイヤーデータを解析して、全員の役名と勝利者をログ欄に強制出力する"""
        if self.printed_showdown_log:
            return

        self.game.action_logs.append(
            "================= 最終結果 (Showdown) ================="
        )
        
        for p in self.game.players:
            if p.is_busted and len(p.hand) == 0:
                self.game.action_logs.append(f" • {p.name}: すでに破産退場済 (BUSTED)")
                continue

            if p.status == HandStatus.FOLDED:
                self.game.action_logs.append(f" • {p.name}: フォールド済")
            else:
                h_name = p.hand_name if p.hand_name else "ハイカード (役なし)"
                cards_str = f"[{p.hand[0]} {p.hand[1]}]" if len(p.hand) == 2 else ""
                busted_note = " ⚠️このゲームで破産" if p.chips <= 0 else ""
                self.game.action_logs.append(
                    f" • {p.name} {cards_str} => 役名: 【{h_name}】{busted_note}"
                )
        
        winners = []
        for log in reversed(self.game.action_logs):
            if "wins" in log or "勝者" in log or "獲得" in log:
                for p in self.game.players:
                    if p.name in log and p.name not in winners:
                        winners.append(p)
        
        if not winners:
            active_players = [p for p in self.game.players if p.status != HandStatus.FOLDED]
            if active_players:
                winners = active_players

        self.game.action_logs.append("--------------------------------------------------------")
        for w in winners:
            w_hand = w.hand_name if w.hand_name else "ハイカード"
            self.game.action_logs.append(f" 🏆【勝者】 {w.name} !!  (役: {w_hand})")
            
        self.game.action_logs.append(
            "========================================================"
        )
        self.printed_showdown_log = True
        self.root.after(0, lambda: self.refresh_table("成果発表"))

    def gui_draw_ui(self, round_name):
        self.root.after(0, self.refresh_table, round_name)
        time.sleep(0.5)

    def gui_handle_human_action(
        self, p, to_call, highest_bet, min_raise_increment, can_raise
    ):
        self.current_to_call = min(to_call, p.chips)
        self.min_raise_inc = min_raise_increment
        self.highest_bet = highest_bet
        self.current_player_obj = p
        self.can_raise = can_raise

        self.root.after(0, self.open_action_window, to_call, can_raise)

        self.action_event.clear()
        self.action_event.wait()

        return self.selected_action

    def open_action_window(self, to_call, can_raise):
        """【配置変更】ウィンドウを完全に画面の「一番右下隅（ログに被る位置）」に密着して表示"""
        if self.is_game_over:
            return

        self.act_win = tk.Toplevel(self.root)
        self.act_win.title("アクション選択")
        self.act_win.geometry("450x150")
        self.act_win.resizable(False, False)
        
        self.act_win.transient(self.root)
        self.act_win.grab_set()

        # 【一番右下隅への密着配置の座標計算】
        # 親ウィンドウの右端（親のX座標 + 親の幅）からポップアップの横幅分（450px）を引き算、
        # 親ウィンドウの下端（親のY座標 + 親の高さ）からポップアップの縦幅分（150px）を引き算することで一番右下に綺麗に重なります。
        self.act_win.update_idletasks()
        rx = self.root.winfo_x() + self.root.winfo_width() - 455
        ry = self.root.winfo_y() + self.root.winfo_height() - 175
        self.act_win.geometry(f"+{int(rx)}+{int(ry)}")

        # 上部の案内テキスト
        p = self.current_player_obj
        info_text = f"あなた（所持: {p.chips}pt）の手番です。アクションを選んでください。"
        tk.Label(self.act_win, text=info_text, font=("Arial", 10, "bold"), pady=10).pack()

        btn_frame = tk.Frame(self.act_win)
        btn_frame.pack(fill="x", expand=True, padx=10, pady=5)

        # 1. フォールドボタン
        btn_fold = tk.Button(
            btn_frame, text="フォールド", width=12, height=2, bg="#cfd8dc",
            command=lambda: self.on_popup_action_click("fold", 0)
        )
        btn_fold.pack(side="left", padx=10, expand=True)

        # 2. チェック / コールボタン
        call_text = "チェック" if to_call == 0 else f"{to_call}pt コール"
        btn_call = tk.Button(
            btn_frame, text=call_text, width=15, height=2, bg="#a5d6a7",
            command=lambda: self.on_popup_action_click("call", self.current_to_call)
        )
        btn_call.pack(side="left", padx=10, expand=True)

        # 3. ベット / レイズボタン
        btn_raise = tk.Button(
            btn_frame, text="ベット / レイズ...", width=15, height=2, bg="#ffab91",
            command=self.on_popup_raise_click
        )
        
        if can_raise and p.chips > to_call:
            raise_text = "ベット" if self.highest_bet == 0 else "レイズ"
            btn_raise.config(text=f"{raise_text}...")
            btn_raise.pack(side="left", padx=10, expand=True)
        else:
            btn_raise.config(state="disabled")
            btn_raise.pack(side="left", padx=10, expand=True)

        self.act_win.protocol("WM_DELETE_WINDOW", lambda: self.on_popup_action_click("fold", 0))

    def on_popup_action_click(self, act_type, amount):
        self.selected_action = (act_type, amount)
        if hasattr(self, 'act_win') and self.act_win.winfo_exists():
            self.act_win.destroy()
        self.action_event.set()

    def on_popup_raise_click(self):
        p = self.current_player_obj
        min_needed = self.highest_bet + self.min_raise_inc
        min_input = min_needed - p.round_bet
        max_input = p.chips

        if min_input > max_input:
            self.on_popup_action_click("raise", p.chips)
            return

        raise_win = tk.Toplevel(self.act_win)
        raise_win.title("金額入力")
        raise_win.geometry("300x150")
        raise_win.transient(self.act_win)
        raise_win.grab_set()

        raise_win.update_idletasks()
        mx = self.act_win.winfo_x() + 75
        my = self.act_win.winfo_y()
        raise_win.geometry(f"+{mx}+{my}")

        label_text = f"上乗せ額を指定してください\n({min_input} 〜 {max_input} pt)"
        if self.highest_bet == 0:
            label_text = f"ベット総額を指定してください\n({min_input} 〜 {max_input} pt)"

        tk.Label(raise_win, text=label_text, justify="center").pack(pady=10)

        val_scale = tk.Scale(raise_win, from_=min_input, to=max_input, orient="horizontal")
        val_scale.pack(fill="x", padx=20)

        def confirm_raise():
            amount = val_scale.get()
            raise_win.destroy()
            self.on_popup_action_click("raise", amount)

        tk.Button(raise_win, text="決定", command=confirm_raise, width=10).pack(pady=10)

    def append_log(self, messages):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        for msg in messages[-15:]:
            self.log_text.insert(tk.END, f" {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def draw_card_object(self, cx, cy, card_obj, is_hidden=False):
        """指定した座標にトランプ風の白い四角いカードを描画するヘルパー関数"""
        card_w, card_h = 36, 50

        if is_hidden:
            self.canvas.create_rectangle(
                cx - card_w / 2, cy - card_h / 2, cx + card_w / 2, cy + card_h / 2,
                fill="#b71c1c", outline="white", width=1
            )
            self.canvas.create_text(cx, cy, text="⚡", fill="white", font=("Arial", 14, "bold"))
        else:
            suit = card_obj.suit
            rank = card_obj.rank
            card_color = "red" if suit in ["♥", "♦"] else "black"

            self.canvas.create_rectangle(
                cx - card_w / 2, cy - card_h / 2, cx + card_w / 2, cy + card_h / 2,
                fill="white", outline="#90a4ae", width=1
            )
            self.canvas.create_text(cx, cy - 10, text=suit, fill=card_color, font=("Arial", 14, "bold"))
            self.canvas.create_text(cx, cy + 12, text=rank, fill=card_color, font=("Arial", 11, "bold"))

    def refresh_table(self, round_name):
        """Canvas全体の再描画"""
        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        center_x = width / 2
        center_y = height / 2 - 40
        rx = min(width * 0.35, 340)
        ry = min(height * 0.25, 170)

        # 1. カジノテーブル外枠
        self.canvas.create_oval(
            center_x - rx, center_y - ry, center_x + rx, center_y + ry,
            fill="#154234", outline="#0f3025", width=10
        )

        total_pot = sum(p.game_bet for p in self.game.players)
        self.canvas.create_text(
            center_x, center_y - 65,
            text=f"【{round_name}】\nTotal Pot: {total_pot} pt",
            fill="#ffb300", font=("Arial", 13, "bold"), justify="center"
        )

        # 2. コミュニティカード
        if self.game.board:
            start_bx = center_x - (len(self.game.board) - 1) * 22
            for idx, card in enumerate(self.game.board):
                self.draw_card_object(start_bx + (idx * 44), center_y, card)
        else:
            self.canvas.create_text(
                center_x, center_y, text="[ コミュニティカード ]",
                font=("Arial", 12), fill="#4d826e"
            )

        # 3. プレイヤーの配置
        players = self.game.players
        num_p = len(players)
        if num_p == 0:
            return

        is_showdown = "ショーダウン" in round_name or "成果発表" in round_name or self.printed_showdown_log

        for i, p in enumerate(players):
            angle_degree = 90 + (i * (360 / num_p))
            angle_radian = math.radians(angle_degree)

            px = center_x + rx * math.cos(angle_radian)
            py = center_y + ry * math.sin(angle_radian)

            box_color = "#263238"
            if p.status == HandStatus.FOLDED:
                box_color = "#555555"
            elif p.status == HandStatus.ALL_IN:
                box_color = "#d32f2f"
            elif p.is_busted:
                box_color = "#1c1c1c"
            elif p.is_human:
                box_color = "#006064"

            d_mark = " [D]" if i == self.game.dealer_idx else ""
            p_name_str = f"{p.name}{d_mark}"

            box_w, box_h = 140, 80
            self.canvas.create_rectangle(
                px - box_w / 2, py - box_h / 2, px + box_w / 2, py + box_h / 2,
                fill=box_color, outline="#cfd8dc" if p.is_human else "black",
                width=2 if p.is_human else 1
            )

            self.canvas.create_text(
                px, py - 25, text=p_name_str,
                fill="#ffeb3b" if p.is_human else "white", font=("Arial", 10, "bold")
            )
            self.canvas.create_text(
                px, py - 10, text=f"Chips: {p.chips}pt",
                fill="#81c784", font=("Arial", 9)
            )

            # 手札カードの描画
            if len(p.hand) == 2 and (p.is_active_in_hand() or (is_showdown and not p.status == HandStatus.FOLDED)):
                show_card = p.is_human or self.debug_mode or is_showdown
                self.draw_card_object(px - 22, py + 18, p.hand[0], not show_card)
                self.draw_card_object(px + 22, py + 18, p.hand[1], not show_card)
            elif p.status == HandStatus.FOLDED:
                self.canvas.create_text(px, py + 18, text="FOLDED", fill="#b0bec5", font=("Arial", 10))

            if p.is_busted and len(p.hand) == 0:
                self.canvas.create_text(px, py + 18, text="BUSTED", fill="#721c24", font=("Arial", 10))

            if p.round_bet > 0:
                self.canvas.create_text(
                    px, py + 48, text=f"Bet: {p.round_bet}pt",
                    fill="#ffab91", font=("Arial", 8, "italic")
                )

        # 4. 敗北（ゲームオーバー）画面
        if self.is_game_over:
            self.canvas.create_rectangle(
                center_x - 250, center_y - 80, center_x + 250, center_y + 80,
                fill="#1a0c0c", outline="#ff1744", width=3
            )
            self.canvas.create_text(
                center_x, center_y - 20, text="GAME OVER",
                fill="#ff1744", font=("Impact", 36, "bold")
            )
            self.canvas.create_text(
                center_x, center_y + 25, text="あなたの所持チップがなくなりました（破産）。",
                fill="white", font=("Arial", 12, "bold")
            )

        self.append_log(self.game.action_logs)


if __name__ == "__main__":
    root = tk.Tk()
    app = TexasHoldemGUI(root)
    root.mainloop()
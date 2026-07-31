import tkinter as tk

class ActionPopup(tk.Toplevel):
    def __init__(self, master, player, to_call, can_raise, min_raise_inc=20):
        super().__init__(master)
        self.title("あなたのアクション")
        self.geometry("340x240")
        self.grab_set()  # ポップアップが閉じるまで他の操作をブロック

        self.player = player
        self.to_call = to_call
        self.min_raise_inc = min_raise_inc

        self.result_action = None
        self.result_amount = 0

        # 情報表示
        tk.Label(self, text=f"👤 プレイヤー: {player['name']}", font=("Arial", 10, "bold")).pack(pady=3)
        tk.Label(self, text=f"💰 所持チップ: {player['chips']} pt").pack(pady=2)
        
        call_text = f"コール必要額: {to_call} pt" if to_call > 0 else "チェック可能 (0 pt)"
        tk.Label(self, text=f"📌 {call_text}", fg="#1976d2", font=("Arial", 9, "bold")).pack(pady=3)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=15)

        # コール / チェック ボタン
        call_label = "チェック" if to_call == 0 else "コール"
        tk.Button(btn_frame, text=call_label, width=9, bg="#4caf50", fg="white", font=("Arial", 9, "bold"),
                  command=lambda: self.finish("call", to_call)).pack(side="left", padx=4)

        # フォールド ボタン
        tk.Button(btn_frame, text="フォールド", width=9, bg="#f44336", fg="white", font=("Arial", 9, "bold"),
                  command=lambda: self.finish("fold", 0)).pack(side="left", padx=4)

        # レイズ ボタン
        if can_raise:
            tk.Button(btn_frame, text="レイズ", width=9, bg="#ff9800", fg="white", font=("Arial", 9, "bold"),
                      command=self.open_raise_window).pack(side="left", padx=4)

    def open_raise_window(self):
        win = tk.Toplevel(self)
        win.title("レイズ額の調整")
        win.geometry("320x220")
        win.grab_set()

        # レイズ範囲の計算
        # 追加上乗せ額の最小値: to_call + min_raise_inc (ただし所持チップを超えない)
        min_raise = min(self.to_call + self.min_raise_inc, self.player['chips'])
        max_raise = self.player['chips']

        tk.Label(win, text="スライダーでレイズ額を調整してください", font=("Arial", 9, "bold")).pack(pady=8)

        # リアルタイム額表示ラベル
        val_label = tk.Label(win, text=f"{min_raise} pt", font=("Arial", 14, "bold"), fg="#e65100")
        val_label.pack(pady=2)

        # スライダー (Scale) ウィジェット
        slider = tk.Scale(
            win, 
            from_=min_raise, 
            to=max_raise, 
            orient=tk.HORIZONTAL, 
            length=250,
            showvalue=False,  # 値表示は自前ラベルで行う
            command=lambda val: val_label.config(text=f"{val} pt")
        )
        slider.set(min_raise)
        slider.pack(pady=5)

        # 便利なショートカットボタン（Min / All-in）
        btn_sub_frame = tk.Frame(win)
        btn_sub_frame.pack(pady=5)

        tk.Button(btn_sub_frame, text="最小額", width=8,
                  command=lambda: slider.set(min_raise)).pack(side="left", padx=5)
        
        tk.Button(btn_sub_frame, text="All-in", width=8, bg="#b71c1c", fg="white",
                  command=lambda: slider.set(max_raise)).pack(side="left", padx=5)

        def ok():
            val = slider.get()
            self.finish("raise", val)
            win.destroy()

        tk.Button(win, text="決定", width=12, bg="#1976d2", fg="white", font=("Arial", 9, "bold"),
                  command=ok).pack(pady=10)

    def finish(self, act, val):
        self.result_action = act
        self.result_amount = val
        self.destroy()
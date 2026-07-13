# action_popup.py
import tkinter as tk

class ActionPopup(tk.Toplevel):
    def __init__(self, master, player, to_call, can_raise):
        super().__init__(master)
        self.title("あなたのアクション")
        self.geometry("300x200")
        self.grab_set()  # ★ ポップアップが閉じるまで他の操作をブロック

        self.result_action = None
        self.result_amount = 0

        tk.Label(self, text=f"プレイヤー: {player['name']}").pack(pady=5)
        tk.Label(self, text=f"所持チップ: {player['chips']}").pack(pady=5)
        tk.Label(self, text=f"コールに必要: {to_call} pt").pack(pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="コール", width=10,
                  command=lambda: self.finish("call", to_call)).pack(side="left", padx=5)

        tk.Button(btn_frame, text="フォールド", width=10,
                  command=lambda: self.finish("fold", 0)).pack(side="left", padx=5)

        if can_raise:
            tk.Button(btn_frame, text="レイズ", width=10,
                      command=self.open_raise_window).pack(side="left", padx=5)

    def open_raise_window(self):
        win = tk.Toplevel(self)
        win.title("レイズ額入力")
        win.geometry("250x120")
        win.grab_set()

        tk.Label(win, text="追加でいくら上乗せしますか？").pack(pady=5)
        entry = tk.Entry(win)
        entry.pack(pady=5)

        def ok():
            try:
                val = int(entry.get())
            except ValueError:
                val = 0
            self.finish("raise", val)
            win.destroy()

        tk.Button(win, text="OK", command=ok).pack(pady=5)

    def finish(self, act, val):
        self.result_action = act
        self.result_amount = val
        self.destroy()
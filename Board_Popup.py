# Board_Popup.py
import tkinter as tk
from tkinter import scrolledtext

class BoardPopup:
    def __init__(self, parent, title="ポーカー実況・チャット掲示板"):
        self.parent = parent
        
        # 別ウィンドウ（Toplevel）を作成
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        # 入力欄のスペースを確保するため、縦幅を少し広げました(550px)
        self.window.geometry("380x550")
        
        # メイン画面のすぐ右隣に自動配置
        self.window.update_idletasks()
        x = parent.winfo_x() + parent.winfo_width() + 10
        y = parent.winfo_y()
        self.window.geometry(f"+{x}+{y}")
        
        # タイトル
        self.label = tk.Label(
            self.window, 
            text="💬 リアルタイムチャット掲示板", 
            font=("Arial", 11, "bold"), 
            pady=10
        )
        self.label.pack()
        
        # チャットログ表示エリア（ここはシステムや過去ログが並ぶ場所なので編集不可のまま）
        self.text_area = scrolledtext.ScrolledText(
            self.window, 
            wrap=tk.WORD, 
            width=40, 
            height=22, # 入力欄のために少しコンパクトに
            font=("MS Gothic", 10),
            bg="#f4f6f9",
            fg="#2c3e50"
        )
        self.text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.config(state=tk.DISABLED)
        
        # ここから下が新しく追加した「書き込み機能」の部品です --
        
        # 入力欄とボタンを横並びにするための枠組み（フレーム）
        input_frame = tk.Frame(self.window)
        input_frame.pack(padx=10, pady=10, fill=tk.X, side=tk.BOTTOM)
        
        # 1. 文字を入力するフォーム（Entry）
        self.entry = tk.Entry(input_frame, font=("MS Gothic", 10))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 【便利機能】キーボードの「Enterキー」を押すだけでも送信できるように設定
        self.entry.bind("<Return>", lambda event: self.send_message())
        
        # 2. 送信ボタン（Button）
        self.send_btn = tk.Button(
            input_frame, 
            text="送信", 
            command=self.send_message, 
            bg="#4caf50", # 見やすい緑色のボタン
            fg="white", 
            font=("Arial", 9, "bold")
        )
        self.send_btn.pack(side=tk.RIGHT)

    def add_message(self, message):
        """外部（システムや自分）からログにメッセージを追記する関数"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f" {message}\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def send_message(self):
        """【新設】ユーザーが入力した文字を読み取って、チャットに書き込む関数"""
        # 入力欄から文字を取得（前後の余計な空白はカット）
        msg = self.entry.get().strip()
        
        if msg:  # 何か文字が入力されている場合だけ処理
            # 「【あなた】: メッセージ」の形で上のログエリアに追加
            self.add_message(f"【あなた】: {msg}")
            # 送信が終わったら、入力欄の中身をきれいに空っぽにする
            self.entry.delete(0, tk.END)

    def clear_board(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        self.text_area.config(state=tk.DISABLED)
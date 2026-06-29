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
        self.text_area.config(state=tk.DISABLED)# Board_Popup.py
import tkinter as tk
from tkinter import scrolledtext
import threading
import os
import gc  # 既存のコードを一切変更せずに、メイン画面のデータを覗き見るための魔法のモジュール
from dotenv import load_dotenv  # .envファイルから設定を読み込む用
from openai import OpenAI

# .env ファイルから環境変数をロード
load_dotenv()

class BoardPopup:
    def __init__(self, parent, title="ポーカー実況・AIアドバイザー"):
        self.parent = parent
        
        # OpenAIクライアントの初期化（.envのOPENAI_API_KEYを自動的に使用します）
        self.ai_client = None
        try:
            self.ai_client = OpenAI()
        except Exception as e:
            print("OpenAIの初期化に失敗しました。.envファイルの設定を確認してください。", e)

        # 別ウィンドウ（Toplevel）を作成
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("400x580") # アドバイスの文章量に合わせて少し広げました
        
        # メイン画面のすぐ右隣に自動配置
        self.window.update_idletasks()
        x = parent.winfo_x() + parent.winfo_width() + 10
        y = parent.winfo_y()
        self.window.geometry(f"+{x}+{y}")
        
        # タイトル
        self.label = tk.Label(
            self.window, 
            text="🤖 AI同席チャット掲示板\n(「#ヒント」や「教えて」でガチ助言をくれます)", 
            font=("Arial", 10, "bold"), 
            pady=8
        )
        self.label.pack()
        
        # チャットログ表示エリア
        self.text_area = scrolledtext.ScrolledText(
            self.window, 
            wrap=tk.WORD, 
            width=40, 
            height=22,
            font=("MS Gothic", 10),
            bg="#f4f6f9",
            fg="#2c3e50"
        )
        self.text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.config(state=tk.DISABLED)
        
        # 入力枠と送信ボタン
        input_frame = tk.Frame(self.window)
        input_frame.pack(padx=10, pady=10, fill=tk.X, side=tk.BOTTOM)
        
        self.entry = tk.Entry(input_frame, font=("MS Gothic", 10))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self.send_message())
        
        self.send_btn = tk.Button(
            input_frame, 
            text="送信", 
            command=self.send_message, 
            bg="#28a745", # コーチっぽい緑色
            fg="white", 
            font=("Arial", 9, "bold")
        )
        self.send_btn.pack(side=tk.RIGHT)

        # 🎭 通常雑談時のAIのキャラクター設定
        self.ai_normal_prompt = (
            "あなたはテキサスホールデムのゲームをユーザーと一緒に特等席で眺めている、フランクなポーカー仲間（AI）です。"
            "専門用語を交えつつ、ユーザーの雑談にフランクなタメ口（日本語）で、短く2〜3文で答えてください。"
        )

        # 🧠 「#ヒント」と言われた時のガチアドバイザープロンプト
        self.ai_coach_prompt = (
            "あなたは世界最高峰のテキサスホールデム・ポーカーのプロコーチです。"
            "ユーザーからアドバイスを求められました。"
            "提示された【現在のポーカーの場の状況】をプロの視点から冷静に分析し、"
            "現在の「手札の強さ」「ポットオッズ（期待値）」「他プレイヤーの残りチップやベット額」を考慮して、"
            "次にとるべき最適なアクション（フォールド、チェック、コール、レイズ、オールインなど）の提案とその理由を、"
            "初心者にも分かりやすく3〜4文程度の敬体（〜です、〜ます）の日本語で丁寧に解説してください。"
        )

    def get_poker_game_status(self):
        """【魔法の関数】gcモジュールを使い、poker_guiのコードを変更せずに戦況を裏から盗み見る"""
        gui_instance = None
        # メモリ上の全オブジェクトから 'TexasHoldemGUI' を探し出す
        for obj in gc.get_objects():
            if type(obj).__name__ == "TexasHoldemGUI":
                gui_instance = obj
                break
                
        if not gui_instance or not gui_instance.game:
            return "【状況データ】現在、ポーカーのゲームが動いていないか、データを取得できません。"
            
        game = gui_instance.game
        status_lines = []
        status_lines.append("【現在のポーカーの場の状況】")
        
        # 1. コミュニティカード（場札）の情報
        board_cards = [str(c) for c in game.board] if game.board else []
        status_lines.append(f"・場に出ている共有カード: {', '.join(board_cards) if board_cards else 'まだ無し（プリフロップ）'}")
        
        # 2. ポットの総額
        total_pot = sum(p.game_bet for p in game.players)
        status_lines.append(f"・現在のポット(賭け金の総額): {total_pot} pt")
        
        # 3. 全プレイヤーの状態スキャン
        status_lines.append("・参加プレイヤー全員の情報:")
        for p in game.players:
            if p.is_human:
                # ユーザー（あなた）の手札
                hand_str = f"[{p.hand[0]}, {p.hand[1]}]" if len(p.hand) == 2 else "配られていない"
                status_lines.append(f"   - あなた(PLAYER): 残りチップ {p.chips}pt, あなたの手札: {hand_str}, 状態: {p.status.name}, このラウンドのベット額: {p.round_bet}pt")
            else:
                # CPUの情報（AIコーチには見えないように手札は伏せるが、チップやベット額は伝える）
                status_lines.append(f"   - {p.name}(CPU): 残りチップ {p.chips}pt, 状態: {p.status.name}, このラウンドのベット額: {p.round_bet}pt")
                
        # 4. あなたのターン中であれば、今求められている選択肢の数値をドッキング
        if getattr(gui_instance, "show_action_panel", False):
            status_lines.append("\n【あなたに回ってきた選択肢のデータ】")
            status_lines.append(f"   - コールするのに必要な額: {getattr(gui_instance, 'current_to_call', 0)} pt")
            if getattr(gui_instance, "can_raise", False):
                human_player = next((p for p in game.players if p.is_human), None)
                my_round_bet = human_player.round_bet if human_player else 0
                min_raise = (getattr(gui_instance, "highest_bet", 0) + getattr(gui_instance, "min_raise_inc", 0)) - my_round_bet
                max_raise = human_player.chips if human_player else 0
                status_lines.append(f"   - レイズ(ベット)可能な範囲: {min_raise} pt から {max_raise} pt まで")
            else:
                status_lines.append("   - 現在はレイズ不可能です（チェック/コール、またはフォールドのみ）")
                
        return "\n".join(status_lines)

    def add_message(self, message):
        """外部（システムや自分）からログにメッセージを追記する"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f" {message}\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def send_message(self):
        msg = self.entry.get().strip()
        if msg:
            self.add_message(f"【あなた】: {msg}")
            self.entry.delete(0, tk.END)
            
            # 🕵️‍♂️ 特定のキーワード判定（「#ヒント」「教えて」「アドバイス」など）
            is_asking_help = any(keyword in msg for keyword in ["#ヒント", "教えて", "おしえて", "アドバイス", "どうすれば"])
            
            # 裏側でAIを動かす
            threading.Thread(target=self.get_ai_response, args=(msg, is_asking_help), daemon=True).start()

    def get_ai_response(self, user_msg, is_asking_help):
        if not self.ai_client:
            self.add_message("🤖【AI】: OpenAIの初期化に失敗しているため、お返事できません。")
            return
            
        try:
            # 1. モードに応じてプロンプトを切り替え
            system_prompt = self.ai_coach_prompt if is_asking_help else self.ai_normal_prompt
            
            messages_payload = []
            messages_payload.append({"role": "system", "content": system_prompt})
            
            # 2. アドバイス請求キーワードが含まれる場合のみ、隠しレポートをAIに添付する
            if is_asking_help:
                poker_status = self.get_poker_game_status()
                messages_payload.append({"role": "system", "content": f"【現在のリアルタイム戦況データ】\n{poker_status}"})
                self.add_message("🤖【AIコーチ】: うむ、状況を分析するからちょっと待ってくれ...")
            
            messages_payload.append({"role": "user", "content": user_msg})
            
            # OpenAI APIの呼び出し（高速・安価な gpt-4o-mini）
            response = self.ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_payload,
                max_tokens=300,
                temperature=0.4 if is_asking_help else 0.7 # アドバイス時はより冷静に
            )
            
            ai_reply = response.choices[0].message.content.strip()
            
            # 3. 画面に出力
            speaker = "🤖【AIコーチ】" if is_asking_help else "🤖【AIプレイヤー】"
            self.add_message(f"{speaker}: {ai_reply}")
            
        except Exception as e:
            self.add_message(f"⚠️【システム】: エラーが発生しました。({str(e)})")

    def clear_board(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        self.text_area.config(state=tk.DISABLED)
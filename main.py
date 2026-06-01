import random

# カードの定義
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


class PokerGame:

    def __init__(self):
        self.deck = [(rank, suit) for suit in SUITS for rank in RANKS]
        self.player_hand = []
        self.cpu_hand = []
        self.community_cards = []
        self.pot = 0

    def shuffle_and_deal(self):
        random.shuffle(self.deck)
        # プリフロップ：お互いに2枚ずつ配る
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.cpu_hand = [self.deck.pop(), self.deck.pop()]

    def show_card(self, card):
        return f"[{card[1]}{card[0]}]"

    def show_cards(self, cards):
        return " ".join([self.show_card(c) for c in cards])

    def betting_round(self, round_name):
        print(f"\n--- {round_name} ベッティングラウンド ---")
        print(f"現在のポット: {self.pot} チップ")
        print(f"あなたの手札: {self.show_cards(self.player_hand)}")
        print(f"場札（コミュニティ）: {self.show_cards(self.community_cards)}")

        # 簡易的なプレイヤーのアクション入力
        while True:
            action = (
                input("アクションを選んでください (1: チェック/コール, 2: ベット/レイズ, 3: フォールド): ")
                .strip()
            )
            if action == "1":
                print("あなた: チェック/コール")
                break
            elif action == "2":
                bet = 20
                self.pot += bet
                print(f"あなた: {bet} チップベットしました。")
                break
            elif action == "3":
                print("あなた: フォールドしました。CPUの勝ちです。")
                return False
            else:
                print("無効な入力です。")

        # 簡易的なCPUのアクション（常にコールすると仮定）
        print("CPU: コール")
        if action == "2":
            self.pot += 20  # CPUも同額出す
        return True

    def play(self):
        print("★ テキサスホールデム ポーカーを開始します ★")
        self.shuffle_and_deal()

        # 1. プリフロップ (手札2枚のみ)
        if not self.betting_round("プリフロップ"):
            return

        # 2. フロップ (場札3枚)
        self.community_cards.extend(
            [self.deck.pop(), self.deck.pop(), self.deck.pop()]
        )
        if not self.betting_round("フロップ"):
            return

        # 3. ターン (場札4枚目)
        self.community_cards.append(self.deck.pop())
        if not self.betting_round("ターン"):
            return

        # 4. リバー (場札5枚目)
        self.community_cards.append(self.deck.pop())
        if not self.betting_round("リバー"):
            return

        # 5. ショーダウン (勝敗開示)
        print("\n--- ショーダウン ---")
        print(f"あなたの手札: {self.show_cards(self.player_hand)}")
        print(f"CPUの手札   : {self.show_cards(self.cpu_hand)}")
        print(f"場のカード  : {self.show_cards(self.community_cards)}")

        print("\n※この簡易版コードでは役判定をスキップします。")
        print(f"総額 {self.pot} チップのポットの分け前は…今回は引き分け、またはあなたの引きの強さに免じてあなたの勝ちとしましょう！")
        print("ゲーム終了です。")


# ゲームの実行
if __name__ == "__main__":
    game = PokerGame()
    game.play()
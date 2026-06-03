import os
import random
from collections import Counter
import itertools

# =====================================================================
# [SECTION 1] 定数・トランプ基本データの定義
# =====================================================================
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}
VALUE_TO_RANK = {v: r for r, v in RANK_VALUES.items()}

HAND_NAMES = {
    9: "ロイヤルストレートフラッシュ", 
    8: "ストレートフラッシュ", 
    7: "フォーカード",
    6: "フルハウス", 
    5: "フラッシュ", 
    4: "ストレート",
    3: "スリーカード", 
    2: "ツーペア", 
    1: "ワンペア", 
    0: "ハイカード"
}


# =====================================================================
# [SECTION 2] データ構造クラス
# =====================================================================
class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = RANK_VALUES[rank]
        
    def __repr__(self):
        return f"[{self.suit}{self.rank}]"


class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)
        
    def draw(self, n):
        return [self.cards.pop() for _ in range(n)]


class Player:
    def __init__(self, player_id, name, chips=1000, is_human=False):
        self.id = player_id
        self.name = name
        self.chips = chips          
        self.is_human = is_human    
        
        # 動的ステータス
        self.hand = []              
        self.active = True          
        self.game_bet = 0           
        self.round_bet = 0          
        self.acted = False          
        self.score = (-1,)          
        self.hand_name = ""         

    def reset_for_new_round(self):
        self.round_bet = 0
        self.acted = False

    def reset_for_new_game(self):
        self.hand = []
        self.active = (self.chips > 0) 
        self.game_bet = 0
        self.round_bet = 0
        self.acted = False
        self.score = (-1,)
        self.hand_name = ""

    def is_all_in(self):
        return self.active and self.chips == 0 and self.game_bet > 0

    def is_playable(self):
        return self.active and self.chips > 0


# =====================================================================
# [SECTION 3] 役の判定ロジック
# =====================================================================
def check_straight(values):
    if len(values) != 5: return False, 0
    if values[0] - values[4] == 4: return True, values[0]
    if set(values) == {14, 5, 4, 3, 2}: return True, 5
    return False, 0

def evaluate_5_cards(cards):
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    
    is_flush = len(set(suits)) == 1 
    unique_values = sorted(list(set(values)), reverse=True) 
    
    is_straight, straight_high = False, 0
    if len(unique_values) == 5:
        is_straight, straight_high = check_straight(unique_values)
        if is_straight and straight_high == 5: 
            values = [5, 4, 3, 2, 1]
            
    counts = Counter(values)
    count_pairs = sorted([(count, val) for val, count in counts.items()], key=lambda x: (x[0], x[1]), reverse=True)
    
    if is_flush and is_straight and straight_high == 14: return (9, 14), HAND_NAMES[9]
    if is_flush and is_straight: return (8, straight_high), f"{VALUE_TO_RANK[straight_high]}ハイ・ストレートフラッシュ"
    if count_pairs[0][0] == 4: return (7, count_pairs[0][1], count_pairs[1][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}のフォーカード"
    if count_pairs[0][0] == 3 and count_pairs[1][0] == 2: return (6, count_pairs[0][1], count_pairs[1][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}と{VALUE_TO_RANK[count_pairs[1][1]]}のフルハウス"
    if is_flush: return (5, tuple(values)), f"{VALUE_TO_RANK[values[0]]}ハイ・フラッシュ"
    if is_straight: return (4, straight_high), f"{VALUE_TO_RANK[straight_high]}ハイ・ストレート"
    if count_pairs[0][0] == 3: return (3, count_pairs[0][1], count_pairs[1][1], count_pairs[2][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}のスリーカード"
    if count_pairs[0][0] == 2 and count_pairs[1][0] == 2: return (2, count_pairs[0][1], count_pairs[1][1], count_pairs[2][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}と{VALUE_TO_RANK[count_pairs[1][1]]}のツーペア"
    if count_pairs[0][0] == 2: return (1, count_pairs[0][1], count_pairs[1][1], count_pairs[2][1], count_pairs[3][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}のワンペア"
    return (0, tuple(values)), f"{VALUE_TO_RANK[values[0]]}ハイ"

def evaluate_7_cards(cards):
    best_score = (-1,)
    best_hand_name = "ハイカード"
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        if score > best_score:
            best_score, best_hand_name = score, name
    return best_score, best_hand_name

def check_draw_opportunity(cards):
    if len(cards) < 4: return False
    if any(count >= 4 for count in Counter([c.suit for c in cards]).values()): return True
    values = set(c.value for c in cards)
    if 14 in values: values.add(1)
    sorted_vals = sorted(list(values))
    for i in range(len(sorted_vals) - 3):
        if sorted_vals[i+3] - sorted_vals[i] <= 4: return True
    return False


# =====================================================================
# [SECTION 4] CPU AI 思考エンジン（【欠陥修正】ブラフ・オールイン対策）
# =====================================================================
def cpu_decision(cpu_cards, board, to_call, cpu_chips):
    """
    相手の無茶なオールインや大ベットに対抗できるようにロジックを強化
    """
    all_cards = cpu_cards + board
    
    # --- プリフロップ（場札がまだ無い状態）の強化AI ---
    if len(board) == 0:
        v1, v2 = cpu_cards[0].value, cpu_cards[1].value
        is_pair = (v1 == v2)
        high_card_sum = v1 + v2
        is_suited = (cpu_cards[0].suit == cpu_cards[1].suit)

        # 相手が大きなベット（30超）をしてきた場合の防御・対抗ロジック
        if to_call > 30:
            # 1. ポケットペア（AA〜77）なら、相手のオールインにも100%コールで立ち向かう
            if is_pair and v1 >= 7: return 1, 0
            # 2. ポケットペア（66以下）なら五分五分で勝負
            if is_pair and random.random() < 0.50: return 1, 0
            # 3. AK, AQ, AJ, KQ などの強力なハイカード（合計25以上）ならコール
            if high_card_sum >= 25: return 1, 0
            # 4. 同じマークの連続（例: 10♥J♥）など、化ける可能性があれば低確率でコール
            if is_suited and abs(v1 - v2) == 1 and random.random() < 0.25: return 1, 0
            
            # それ以外のゴミ手札なら、ハメ技防止のためフォールド
            return 3, 0
        
        # 通常の安いベット（コール額が小さい）なら従来通り参加
        else:
            if is_pair or high_card_sum >= 20 or is_suited:
                if high_card_sum >= 26 and random.random() < 0.2: return 2, min(40, cpu_chips) # たまにレイズ
                return 1, 0
            if to_call <= 20: return 1, 0 # BB決済用
            return 3, 0

    # --- フロップ以降（場札がある状態）のAI ---
    score_idx = evaluate_7_cards(all_cards)[0][0]
    is_draw = check_draw_opportunity(all_cards)
    
    if to_call == 0:
        if score_idx >= 2 or (random.random() < 0.10): return 2, min(40, cpu_chips)
        return 1, 0
    else:
        # 相手がオールイン等で大きく賭けてきた時
        if to_call >= 150:
            if score_idx >= 3: return 1, 0 # スリーカード以上なら受けて立つ
            if score_idx == 2 and random.random() < 0.7: return 1, 0 # ツーペアでも高確率で勝負
            if score_idx == 1 and max(v.value for v in cpu_cards) >= 13 and random.random() < 0.3: return 1, 0 # 強いワンペア
            return 3, 0 # それ以外は降りる
            
        # 通常のベットへの対抗
        if score_idx >= 3:
            if cpu_chips > to_call and random.random() < 0.3: return 2, min(to_call + 40, cpu_chips)
            return 1, 0
        if score_idx in [1, 2]:
            return 1, 0
        if score_idx == 0:
            if is_draw and to_call <= 100: return 1, 0
            if to_call <= 30: return 1, 0
            return 3, 0
        return 1, 0


# =====================================================================
# [SECTION 5] ゲーム進行・管理クラス
# =====================================================================
class TexasHoldemGame:
    def __init__(self):
        self.players = []          
        self.board = []            
        self.deck = None           
        self.dealer_idx = -1       
        self.action_logs = []      
        self.debug_mode = False    

    def add_log(self, text):
        self.action_logs.append(text)

    def draw_ui(self, round_name):
        total_pot = sum(p.game_bet for p in self.players)
        
        print("\n" + "#" * 70)
        print(f"### DEBUG SNAPSHOT: {round_name} ###  [総ポット: {total_pot} チップ]")
        print("#" * 70)
        
        half = (len(self.players) + 1) // 2
        for i in range(half):
            p1 = self.players[i]
            d1 = "[D]" if i == self.dealer_idx else "   "
            status1 = "FOLD" if not p1.active else f"Bet:{p1.round_bet}"
            if p1.is_all_in(): status1 = "ALL-IN"
            p1_str = f"{d1} {p1.name:<6}: {p1.chips:>4}pt ({status1})"
            
            if i + half < len(self.players):
                p2 = self.players[i + half]
                d2 = "[D]" if (i + half) == self.dealer_idx else "   "
                status2 = "FOLD" if not p2.active else f"Bet:{p2.round_bet}"
                if p2.is_all_in(): status2 = "ALL-IN"
                p2_str = f"{d2} {p2.name:<6}: {p2.chips:>4}pt ({status2})"
                print(f"{p1_str:<35} | {p2_str}")
            else:
                print(p1_str)
                
        print(f"場札 (Board): {' '.join(map(str, self.board)) if self.board else '[ まだ開いていません ]'}")
        print(f"----------------------------------------------------------------------")
        print(f"【このラウンドのアクション履歴】")
        if not self.action_logs: 
            print("  （なし）")
        else:
            for log in self.action_logs[-8:]: 
                print(f"  • {log}")
        print(f"----------------------------------------------------------------------")

    def run_betting_round(self, round_name):
        self.action_logs.clear()
        
        for p in self.players:
            p.reset_for_new_round()

        if round_name == "プリフロップ":
            for p in self.players:
                p.round_bet = p.game_bet  

        def count_active(): return sum(1 for p in self.players if p.active)
        def count_playable(): return sum(1 for p in self.players if p.is_playable())

        num_players = len(self.players)
        start_offset = (3 if num_players > 2 else 1) if round_name == "プリフロップ" else 1
        current_pos = (self.dealer_idx + start_offset) % num_players
        highest_bet = max(p.round_bet for p in self.players)
        min_raise_increment = 20 

        while True:
            if count_active() <= 1 or count_playable() == 0: break
            
            all_settled = True
            for p in self.players:
                if p.active and p.is_playable():
                    if not p.acted or p.round_bet != highest_bet:
                        all_settled = False
            if all_settled: break

            p = self.players[current_pos]
            if not p.active or p.chips == 0:
                current_pos = (current_pos + 1) % num_players
                continue

            # 【バグ修正】コールに必要な額の算出をより正確に
            to_call = highest_bet - p.round_bet
            self.draw_ui(round_name)

            # --- 人間の行動 ---
            if p.is_human:
                print(f"【あなたの番】 所持: {p.chips} | コールに必要な額: {to_call}")
                print(f"あなたの手札:  {p.hand[0]} {p.hand[1]}")
                
                while True:
                    action = input("アクション（1:コール/チェック, 2:ベット/レイズ, 3:フォールド）: ").strip()
                    if action in ["1", "2", "3"]: break
                    print("1, 2, 3 のいずれかを入力してください。")

                if action == "1":
                    call_amnt = min(to_call, p.chips)
                    p.chips -= call_amnt
                    p.round_bet += call_amnt
                    p.game_bet += call_amnt
                    self.add_log(f"あなた: {'チェック' if call_amnt == 0 else f'{call_amnt}でコール'}{'（All-in!）' if p.chips==0 else ''}")
                    p.acted = True
                    
                elif action == "2":
                    action_title = "ベット" if highest_bet == 0 else "レイズ"
                    min_needed = highest_bet + (min_raise_increment if highest_bet > 0 else 20)
                    min_input = min_needed - p.round_bet
                    max_input = p.chips

                    if max_input <= to_call:
                        input("チップが足りないためレイズできません。[Enter]で戻る")
                        continue

                    print(f"追加額を指定してください ({min_input} 〜 {max_input})")
                    while True:
                        try:
                            raise_val = int(input(f"追加額: "))
                            if min_input <= raise_val <= max_input: break
                            print("範囲外です。")
                        except ValueError: print("数字を入力してください。")

                    p.chips -= raise_val
                    p.round_bet += raise_val
                    p.game_bet += raise_val
                    
                    diff = p.round_bet - highest_bet
                    if diff > min_raise_increment: min_raise_increment = diff
                    highest_bet = p.round_bet
                    
                    self.add_log(f"あなた: 合計{p.round_bet}に{action_title}!決死のAll-in!" if p.chips==0 else f"あなた: 合計{p.round_bet}に{action_title}!")
                    
                    for pl in self.players: 
                        if pl.id != p.id: pl.acted = False
                    p.acted = True

                elif action == "3":
                    self.add_log("あなた: フォールド")
                    p.active = False
                    p.acted = True

            # --- CPUの行動 ---
            else:
                cpu_act, cpu_val = cpu_decision(p.hand, self.board, to_call, p.chips)
                if cpu_act == 2 and p.chips <= to_call: cpu_act = 1

                if cpu_act == 1:
                    call_amnt = min(to_call, p.chips)
                    p.chips -= call_amnt
                    p.round_bet += call_amnt
                    p.game_bet += call_amnt
                    self.add_log(f"{p.name}: {'チェック' if call_amnt == 0 else f'{call_amnt}でコール'}{'（All-in!）' if p.chips==0 else ''}")
                    p.acted = True
                    
                elif cpu_act == 2:
                    action_title = "ベット" if highest_bet == 0 else "レイズ"
                    min_needed = highest_bet + (min_raise_increment if highest_bet > 0 else 20)
                    actual_add = min(max(min_needed - p.round_bet, cpu_val), p.chips)

                    p.chips -= actual_add
                    p.round_bet += actual_add
                    p.game_bet += actual_add
                    
                    diff = p.round_bet - highest_bet
                    if diff > min_raise_increment: min_raise_increment = diff
                    highest_bet = p.round_bet
                    
                    self.add_log(f"{p.name}: 合計{p.round_bet}に{action_title}{'（All-in!）' if p.chips==0 else ''}")
                    
                    for pl in self.players: 
                        if pl.id != p.id: pl.acted = False
                    p.acted = True

                elif cpu_act == 3:
                    self.add_log(f"{p.name}: フォールド")
                    p.active = False
                    p.acted = True

            current_pos = (current_pos + 1) % num_players


    def resolve_showdown(self):
        print("\n" + "=" * 70)
        print(" 🔥 [LOG] ショーダウン & 結果発表 🔥")
        print("=" * 70)
        
        showdown_players = [p for p in self.players if p.active]
        for p in showdown_players:
            score, name = evaluate_7_cards(p.hand + self.board)
            p.score = score
            p.hand_name = name
            print(f" 🃏 {p.name:<6}: {p.hand[0]} {p.hand[1]} -> 【{name}】")

        if showdown_players:
            overall_max_score = max(p.score for p in showdown_players)
            best_hands = [p for p in showdown_players if p.score == overall_max_score]
            print("----------------------------------------------------------------------")
            if len(best_hands) == 1:
                print(f" 🏆 勝者: {best_hands[0].name} !! ({best_hands[0].hand_name})")
            else:
                winner_names = " と ".join(w.name for w in best_hands)
                print(f" 🤝 引き分け: {winner_names} ({best_hands[0].hand_name})")
        print("======================================================================\n")

        has_all_in_showdown = any(p.is_all_in() for p in self.players)

        if not has_all_in_showdown:
            total_pot = sum(p.game_bet for p in self.players)
            if total_pot > 0 and showdown_players:
                max_score = max(p.score for p in showdown_players)
                winners = [p for p in showdown_players if p.score == max_score]
                share = total_pot // len(winners)
                remainder = total_pot % len(winners)
                
                for i, w in enumerate(winners):
                    bonus = 1 if i < remainder else 0
                    w.chips += (share + bonus)
                    print(f" 💰 【計算ログ】メインポット(総額:{total_pot}) から {w.name} へ {share + bonus} チップ分配")
            return

        all_bets = sorted(list(set(p.game_bet for p in self.players if p.game_bet > 0)))
        previous_level = 0
        
        for level in all_bets:
            layer_pot = 0
            eligible_players = []
            
            for p in self.players:
                if p.game_bet >= level:
                    layer_pot += (level - previous_level)
                    if p.active: eligible_players.append(p)
                else:
                    contribution = p.game_bet - previous_level
                    if contribution > 0: layer_pot += contribution
            
            if layer_pot == 0: continue
            if not eligible_players:
                survivors = [p for p in self.players if p.active]
                if survivors: eligible_players = survivors
                else: break

            if eligible_players:
                max_score = max(p.score for p in eligible_players)
                winners = [p for p in eligible_players if p.score == max_score]
                share = layer_pot // len(winners)
                remainder = layer_pot % len(winners)
                
                for i, w in enumerate(winners):
                    bonus = 1 if i < remainder else 0
                    w.chips += (share + bonus)
                    pot_name = "メインポット" if previous_level == 0 else "サイドポット"
                    print(f" 💰 【計算ログ】{pot_name}(総額:{layer_pot}) から {w.name} へ {share + bonus} チップ分配")
                    
            previous_level = level

    def start_game_loop(self):
        print("=========================================")
        print("♠♥♦♣ MULTI-PLAYER TEXAS HOLD'EM POKER ♣♦♥♠")
        print("=========================================")
        
        while True:
            try:
                num_p = int(input("プレイ人数を入力してください (2 〜 6人): ").strip())
                if 2 <= num_p <= 6: break
                print("2から6の間で入力してください。")
            except ValueError: print("正しい数値を入力してください。")

        db_input = input("デバッグモード（全員の手札を常時ログに表示）にしますか？ (y/n): ").strip().lower()
        self.debug_mode = (db_input == 'y')

        self.players.append(Player(0, "あなた", chips=1000, is_human=True))
        for i in range(1, num_p):
            self.players.append(Player(i, f"CPU {i}", chips=1000, is_human=False))

        games_count = 0

        while True:
            active_list = [p for p in self.players if p.chips > 0]
            
            if not any(p.is_human for p in active_list):
                print("\nあなたの所持チップがなくなりました。ゲームオーバー！")
                break
            if len(active_list) == 1 and active_list[0].is_human:
                print("\nあなた以外の全員を破産させました！完全勝利です！！")
                break

            games_count += 1
            print(f"\n\n🚨 ==================== 【 第 12 回 戦 開 始 】 ==================== 🚨" if games_count==12 else f"\n\n🚨 ==================== 【 第 {games_count} 回 戦 開 始 】 ==================== 🚨")
            
            self.board.clear()
            self.deck = Deck()

            for p in self.players:
                p.reset_for_new_game()

            while True:
                self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
                if self.players[self.dealer_idx].chips > 0: break
            
            idx_in_actives = active_list.index(self.players[self.dealer_idx])
            if len(active_list) == 2: 
                sb_p = active_list[idx_in_actives]
                bb_p = active_list[(idx_in_actives + 1) % len(active_list)]
            else:
                sb_p = active_list[(idx_in_actives + 1) % len(active_list)]
                bb_p = active_list[(idx_in_actives + 2) % len(active_list)]

            sb_amnt = min(10, sb_p.chips)
            bb_amnt = min(20, bb_p.chips)
            sb_p.chips -= sb_amnt
            sb_p.game_bet += sb_amnt
            bb_p.chips -= bb_amnt
            bb_p.game_bet += bb_amnt

            print(f" 📢 【システム】{sb_p.name} がSB({sb_amnt})を支払いました。")
            print(f" 📢 【システム】{bb_p.name} がBB({bb_amnt})を支払いました。")

            for p in active_list:
                p.hand = self.deck.draw(2)
                if self.debug_mode and not p.is_human:
                    print(f" [DEBUG] {p.name} の配られた手札: {p.hand[0]}{p.hand[1]}")

            self.run_betting_round("プリフロップ")

            for phase in ["フロップ", "ターン", "リバー"]:
                if sum(1 for p in self.players if p.active) > 1 and sum(1 for p in self.players if p.is_playable()) >= 1:
                    self.board.extend(self.deck.draw(3 if phase == "フロップ" else 1))
                    self.run_betting_round(phase)

            if sum(1 for p in self.players if p.active) == 1:
                winner = next(p for p in self.players if p.active)
                total_pot = sum(p.game_bet for p in self.players)
                winner.chips += total_pot
                print(f"\n 全員がフォールドしたため、{winner.name} の不戦勝です！\n 💰 {total_pot} チップを獲得。")
            else:
                self.resolve_showdown()

            for p in active_list:
                if p.chips <= 0:
                    print(f"📢 【アナウンス】{p.name} が破産（トビ）しました。")

            active_list_next = [p for p in self.players if p.chips > 0]
            if not any(p.is_human for p in active_list_next) or (len(active_list_next) == 1 and active_list_next[0].is_human):
                continue

            cmd = input("\n--- [Enter] で次のゲームへ / (q)で終了 --- ").strip().lower()
            if cmd == 'q':
                break


if __name__ == "__main__":
    game = TexasHoldemGame()
    game.start_game_loop()
import os
import random
from collections import Counter
import itertools
import sys
from enum import Enum, auto

# =====================================================================
# [SECTION 1] 定数・構造体・エナムの定義
# =====================================================================
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}
VALUE_TO_RANK = {v: r for r, v in RANK_VALUES.items()}

class HandStatus(Enum):
    PLAYING = auto()  
    FOLDED = auto()   
    ALL_IN = auto()   

class GameStructure:
    def __init__(self, sb=10, bb=20, min_raise_inc=20):
        self.SB = sb
        self.BB = bb
        self.MIN_RAISE_INCREMENT = min_raise_inc

HAND_NAMES = {
    9: "ロイヤルストレートフラッシュ", 8: "ストレートフラッシュ", 7: "フォーカード",
    6: "フルハウス", 5: "フラッシュ", 4: "ストレート",
    3: "スリーカード", 2: "ツーペア", 1: "ワンペア", 0: "ハイカード"
}


# =====================================================================
# [SECTION 2] データ構造・オブジェクトクラス
# =====================================================================
class Card:
    def __init__(self, suit, rank):
        if suit not in SUITS or rank not in RANKS:
            raise ValueError(f"不正なカードデータ: {suit}{rank}")
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
        if len(self.cards) < n:
            raise ValueError(f"山札不足。 要求枚数: {n}, 残り: {len(self.cards)}")
        return [self.cards.pop() for _ in range(n)]


class Player:
    def __init__(self, player_id, name, chips=1000, is_human=False):
        self.id = player_id
        self.name = name
        self.chips = chips          
        self.is_human = is_human    
        
        self.status = HandStatus.PLAYING
        self.is_busted = False       
        self.hand = []              
        self.game_bet = 0           
        self.round_bet = 0          
        self.acted = False          
        self.score = (-1,)          
        self.hand_name = ""         

    def reset_for_new_round(self):
        self.round_bet = 0
        if self.status == HandStatus.PLAYING:
            self.acted = False
        elif self.status == HandStatus.ALL_IN:
            self.acted = True

    def reset_for_new_game(self):
        self.hand = []
        self.game_bet = 0
        self.round_bet = 0
        self.acted = False
        self.score = (-1,)
        self.hand_name = ""
        if self.chips <= 0:
            self.chips = 0
            self.is_busted = True
            self.status = HandStatus.FOLDED
        else:
            if not self.is_busted:
                self.status = HandStatus.PLAYING

    def is_active_in_hand(self):
        return (not self.is_busted) and (self.status != HandStatus.FOLDED)

    def can_make_action(self):
        return self.is_active_in_hand() and (self.status == HandStatus.PLAYING)


# =====================================================================
# [SECTION 3] ポーカー会計システム（サイドポット完全保証版）
# =====================================================================
class SidePot:
    def __init__(self, amount=0):
        self.amount = amount
        self.eligible_player_ids = []


class PotManager:
    def __init__(self):
        self.pots = []

    def build_pots(self, players):
        self.pots.clear()
        
        # チップを場に出したすべてのプレイヤーのベット額の階層リストを作成
        active_bets = sorted(list(set(p.game_bet for p in players if p.game_bet > 0)))
        previous_level = 0
        
        for level in active_bets:
            current_pot = SidePot()
            pot_chips = 0
            
            for p in players:
                # プレイヤーがこの階層以上のベットを行っている場合
                if p.game_bet >= level:
                    pot_chips += (level - previous_level)
                    # 該当階層への権利があり、かつフォールドもトビもしていないプレイヤーを受給資格者とする
                    if p.status != HandStatus.FOLDED and not p.is_busted:
                        current_pot.eligible_player_ids.append(p.id)
                else:
                    # この階層未満しか出していない場合、出せる全額を回収
                    contribution = p.game_bet - previous_level
                    if contribution > 0:
                        pot_chips += contribution
            
            if pot_chips > 0:
                current_pot.amount = pot_chips
                # 万が一、このポットへの出資者が全員フォールド等で消えていた場合、生存者全員を救済対象にする
                if not current_pot.eligible_player_ids:
                    current_pot.eligible_player_ids = [pl.id for pl in players if pl.status != HandStatus.FOLDED and not pl.is_busted]
                self.pots.append(current_pot)
                
            previous_level = level

    def distribute_pots(self, players):
        log_messages = []
        self.build_pots(players)
        player_dict = {p.id: p for p in players}
        
        showdown_survivors = [p for p in players if p.status != HandStatus.FOLDED and not p.is_busted]
        
        for idx, pot in enumerate(self.pots):
            if pot.amount == 0:
                continue
                
            eligible_winners = [player_dict[pid] for pid in pot.eligible_player_ids if player_dict[pid].status != HandStatus.FOLDED and not player_dict[pid].is_busted]
            
            # 受給資格者が全滅している場合は、ショーダウン生存者（それもいなければ破産していない全員）で分ける
            if not eligible_winners:
                eligible_winners = showdown_survivors if showdown_survivors else [p for p in players if not p.is_busted]
            
            max_score = max(p.score for p in eligible_winners)
            winners = [p for p in eligible_winners if p.score == max_score]
            
            share = pot.amount // len(winners)
            remainder = pot.amount % len(winners)
            
            pot_label = "メインポット" if idx == 0 else f"サイドポット [{idx}]"
            
            distributed_sum = 0
            for i, w in enumerate(winners):
                bonus = 1 if i < remainder else 0
                exact_payout = share + bonus
                w.chips += exact_payout
                distributed_sum += exact_payout
                log_messages.append(f" 💰 【会計ログ】{pot_label}(総額:{pot.amount}) から {w.name} へ {exact_payout}pt 分配しました。")
            
            # 割り切れなかった絶対的な端数はリストの先頭の勝者に集約
            if distributed_sum != pot.amount:
                diff = pot.amount - distributed_sum
                winners[0].chips += diff
                log_messages.append(f" 💰 【会計ログ端数調整】誤差 {diff}pt を {winners[0].name} に集約しました。")
                
        return log_messages


# =====================================================================
# [SECTION 4] 役判定 & ドロー判定エンジン
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
    if len(cards) < 5:
        raise ValueError(f"役判定の防御壁: 最低5枚必要です。現在 {len(cards)}枚")
    best_score = (-1,)
    best_hand_name = "ハイカード"
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        if score > best_score:
            best_score, best_hand_name = score, name
    return best_score, best_hand_name

def check_draw_opportunity(cards):
    if len(cards) < 4: return False
    if any(count == 4 for count in Counter([c.suit for c in cards]).values()):
        return True
    values = set(c.value for c in cards)
    if 14 in values: 
        values.add(1)
    for start in range(1, 12):
        window = set(range(start, start + 5))
        if len(window.intersection(values)) == 4:
            return True
    return False


# =====================================================================
# [SECTION 5] 相対評価型 CPU AI 思考エンジン
# =====================================================================
def cpu_decision(cpu_cards, board, to_call_bb, cpu_chips_bb):
    all_cards = cpu_cards + board
    
    if len(board) == 0:
        v1, v2 = cpu_cards[0].value, cpu_cards[1].value
        is_pair = (v1 == v2)
        high_card_sum = v1 + v2
        is_suited = (cpu_cards[0].suit == cpu_cards[1].suit)

        if to_call_bb > 0:
            if is_pair and v1 >= 5: return 1, 0  
            if high_card_sum >= 20: return 1, 0  
            if is_suited and abs(v1 - v2) <= 2: return 1, 0
            if to_call_bb <= 1.0: return 1, 0 
            return 3, 0 
        else:
            if is_pair or high_card_sum >= 22:
                return 2, min(2.0, cpu_chips_bb) 
            return 1, 0

    score_idx = evaluate_7_cards(all_cards)[0][0]
    is_draw = check_draw_opportunity(all_cards)
    
    if to_call_bb == 0:
        if score_idx >= 2 or (random.random() < 0.10): return 2, min(2.0, cpu_chips_bb)
        return 1, 0
    else:
        if to_call_bb >= 7.5:
            if score_idx >= 3: return 1, 0 
            if score_idx == 2 and random.random() < 0.7: return 1, 0
            if score_idx == 1 and max(v.value for v in cpu_cards) >= 13 and random.random() < 0.3: return 1, 0
            return 3, 0
            
        if score_idx >= 3:
            if cpu_chips_bb > to_call_bb and random.random() < 0.3: return 2, min(to_call_bb + 2.0, cpu_chips_bb)
            return 1, 0
        if score_idx in [1, 2]:
            return 1, 0
        if score_idx == 0:
            if is_draw and to_call_bb <= 5.0: return 1, 0
            if to_call_bb <= 1.5: return 1, 0
            return 3, 0
        return 1, 0


# =====================================================================
# [SECTION 6] ゲーム進行・管理クラス
# =====================================================================
class TexasHoldemGame:
    def __init__(self):
        self.players = []          
        self.board = []            
        self.deck = None           
        self.dealer_idx = -1       
        self.action_logs = []      
        self.debug_mode = False    
        
        self.rules = GameStructure()   
        self.pot_manager = PotManager() 

    def safe_input(self, prompt):
        try:
            return input(prompt)
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 ゲームが強制終了されました。プログラムを安全にシャットダウンします。")
            sys.exit(0)

    def verify_chip_integrity(self, context_label):
        total_current_chips = sum(p.chips for p in self.players) + sum(p.game_bet for p in self.players)
        expected_total = len(self.players) * 1000
        if total_current_chips != expected_total:
            raise AssertionError(f"[致命的な会計監査エラー: {context_label}] 理論値:{expected_total}pt, 実測値:{total_current_chips}pt")

    def add_log(self, text):
        self.action_logs.append(text)

    def draw_ui(self, round_name):
        total_pot = sum(p.game_bet for p in self.players)
        print("\n" + "#" * 70)
        print(f"### ROUND SNAPSHOT: {round_name} ###  [場にある総チップ: {total_pot} pt]")
        print("#" * 70)
        
        half = (len(self.players) + 1) // 2
        for i in range(half):
            p1 = self.players[i]
            d1 = "[D]" if i == self.dealer_idx else "   "
            status1 = p1.status.name if p1.status != HandStatus.PLAYING else f"Bet:{p1.round_bet}"
            if p1.is_busted: status1 = "BUSTED"
            p1_str = f"{d1} {p1.name:<6}: {p1.chips:>4}pt ({status1})"
            
            if i + half < len(self.players):
                p2 = self.players[i + half]
                d2 = "[D]" if (i + half) == self.dealer_idx else "   "
                status2 = p2.status.name if p2.status != HandStatus.PLAYING else f"Bet:{p2.round_bet}"
                if p2.is_busted: status2 = "BUSTED"
                p2_str = f"{d2} {p2.name:<6}: {p2.chips:>4}pt ({status2})"
                print(f"{p1_str:<35} | {p2_str}")
            else:
                print(p1_str)
                
        print(f"場札 (Board): {' '.join(map(str, self.board)) if self.board else '[ まだ開いていません ]'}")
        print(f"----------------------------------------------------------------------")
        print(f"【アクション履歴】")
        for log in self.action_logs[-6:]: print(f"  • {log}")
        print(f"----------------------------------------------------------------------")

    def handle_human_action(self, p, to_call, highest_bet, min_raise_increment, can_raise):
        call_label = "チェック" if to_call == 0 else f"{to_call}ptでコール"
        print(f"【あなたの番】 所限: {p.chips}pt | アクションに必要な額: {call_label}")
        print(f"あなたの手札:  {p.hand[0]} {p.hand[1]}")
        
        raise_label = "ベット" if highest_bet == 0 else "レイズ"
        
        min_needed = highest_bet + min_raise_increment
        min_input = min_needed - p.round_bet
        max_input = p.chips

        is_all_in_raise = False
        if can_raise:
            if max_input <= to_call:
                can_raise = False
            elif min_input > max_input:
                raise_label = "強制オールイン・レイズ"
                is_all_in_raise = True

        while True:
            menu_str = f"アクション（1:{'チェック' if to_call == 0 else 'コール'}"
            if can_raise:
                menu_str += f", 2:{raise_label}"
            menu_str += ", 3:フォールド）: "
            
            action = self.safe_input(menu_str).strip()
            if action == "1" or action == "3": break
            if action == "2" and can_raise: break
            print("有効な選択肢を入力してください。")
            
        if action == "1":
            return "call", min(to_call, p.chips)
        elif action == "2":
            if is_all_in_raise:
                return "raise", p.chips
                
            if highest_bet == 0:
                print(f"ベットする【総額】を指定してください ({min_input} 〜 {max_input}pt)")
            else:
                print(f"現在のBet({p.round_bet}pt)に【追加上乗せ】する額を指定してください ({min_input} 〜 {max_input}pt)")
                
            while True:
                try:
                    raise_val = int(self.safe_input("金額入力: "))
                    if min_input <= raise_val <= max_input: break
                    print("範囲外です。")
                except ValueError: print("数字を入力してください。")
            return "raise", raise_val
        return "fold", 0

    def handle_cpu_action(self, p, to_call, can_raise):
        to_call_bb = to_call / self.rules.BB
        cpu_chips_bb = p.chips / self.rules.BB
        
        cpu_act, cpu_val_pt = cpu_decision(p.hand, self.board, to_call_bb, cpu_chips_bb)
        
        if cpu_act == 2 and not can_raise: 
            cpu_act = 1
        if cpu_act == 2 and p.chips <= to_call: 
            cpu_act = 1
        
        if cpu_act == 1:
            return "call", min(to_call, p.chips)
        elif cpu_act == 2:
            return "raise", min(max(to_call + self.rules.MIN_RAISE_INCREMENT, int(cpu_val_pt * self.rules.BB)), p.chips)
        return "fold", 0

    def apply_action(self, p, action_type, amount, highest_bet, min_raise_increment):
        if action_type == "call":
            p.chips -= amount
            p.round_bet += amount
            p.game_bet += amount
            if p.chips == 0: p.status = HandStatus.ALL_IN
            self.add_log(f"{p.name}: {'チェック' if amount == 0 else f'{amount}ptでコール'}{'（All-in!）' if p.chips==0 else ''}")
            p.acted = True
            return highest_bet, min_raise_increment

        elif action_type == "raise":
            p.chips -= amount
            p.round_bet += amount
            p.game_bet += amount
            
            actual_increment = p.round_bet - highest_bet
            action_title = "ベット" if highest_bet == 0 else "レイズ"
            highest_bet = p.round_bet
            
            if actual_increment >= min_raise_increment:
                min_raise_increment = actual_increment
                for pl in self.players:
                    if pl.id != p.id and pl.status == HandStatus.PLAYING:
                        pl.acted = False  
                        
            if p.chips == 0: p.status = HandStatus.ALL_IN
            self.add_log(f"{p.name}: 合計{p.round_bet}ptに{action_title}!{'（All-in!）' if p.chips==0 else ''}")
            p.acted = True
            return highest_bet, min_raise_increment

        elif action_type == "fold":
            p.status = HandStatus.FOLDED
            p.acted = True
            self.add_log(f"{p.name}: フォールド")
            return highest_bet, min_raise_increment

    def run_betting_round(self, round_name):
        self.action_logs.clear()
        for p in self.players: p.reset_for_new_round()
        if round_name == "プリフロップ":
            for p in self.players: p.round_bet = p.game_bet  

        def count_playable(): return sum(1 for p in self.players if p.can_make_action())
        def count_alive(): return sum(1 for p in self.players if p.is_active_in_hand())

        active_p_list = [p for p in self.players if not p.is_busted]
        num_active = len(active_p_list)
        if num_active == 0: return
        
        dealer_active_idx = next((i for i, p in enumerate(active_p_list) if p.id == self.dealer_idx), 0)
        
        if num_active == 2:
            if round_name == "プリフロップ":
                list_cursor = dealer_active_idx  
            else:
                list_cursor = (dealer_active_idx + 1) % num_active 
        else:
            start_offset = 3 if round_name == "プリフロップ" else 1
            list_cursor = (dealer_active_idx + start_offset) % num_active

        highest_bet = max(p.round_bet for p in self.players)
        min_raise_increment = self.rules.MIN_RAISE_INCREMENT

        while True:
            if count_alive() <= 1 or count_playable() == 0: break
            
            all_settled = True
            for p in self.players:
                if p.can_make_action():
                    if not p.acted or p.round_bet != highest_bet:
                        all_settled = False
            if all_settled: break

            p = active_p_list[list_cursor]
            if not p.can_make_action():
                list_cursor = (list_cursor + 1) % num_active
                continue

            to_call = highest_bet - p.round_bet
            
            can_raise = True
            if p.acted and to_call > 0:
                can_raise = False

            self.draw_ui(round_name)

            if p.is_human:
                act_type, act_val = self.handle_human_action(p, to_call, highest_bet, min_raise_increment, can_raise)
            else:
                act_type, act_val = self.handle_cpu_action(p, to_call, can_raise)

            highest_bet, min_raise_increment = self.apply_action(p, act_type, act_val, highest_bet, min_raise_increment)
            list_cursor = (list_cursor + 1) % num_active


    def start_game_loop(self):
        print("=========================================")
        print("♠♥♦♣ MULTI-PLAYER TEXAS HOLD'EM POKER ♣♦♥♠")
        print("=========================================")
        
        while True:
            try:
                num_p = int(self.safe_input("プレイ人数を入力してください (2 〜 6人): ").strip())
                if 2 <= num_p <= 6: break
                print("2から6の間で入力してください。")
            except ValueError: print("正しい数値を入力してください。")

        db_input = self.safe_input("デバッグモード（全員の手札を常時ログに表示）にしますか？ (y/n): ").strip().lower()
        self.debug_mode = (db_input == 'y')

        self.players.append(Player(0, "あなた", chips=1000, is_human=True))
        for i in range(1, num_p):
            self.players.append(Player(i, f"CPU {i}", chips=1000, is_human=False))

        games_count = 0

        while True:
            # 🛡️ 【絶対防衛線 1】ゲームのループ先頭で「チップを持たないプレイヤー」を確実に排除（即時破産処理）
            for p in self.players:
                if p.chips <= 0 and not p.is_busted:
                    p.chips = 0
                    p.is_busted = True
                    p.status = HandStatus.FOLDED

            living_players = [p for p in self.players if not p.is_busted]
            
            if not any(p.is_human for p in living_players):
                print("\nあなたの所持チップがなくなりました。ゲームオーバー！")
                break
            if len(living_players) == 1 and living_players[0].is_human:
                print("\nあなた以外の全員を破産させました！完全勝利です！！")
                break

            games_count += 1
            print(f"\n\n🚨 ==================== 【 第 {games_count} 回 戦 開 始 】 ==================== 🚨")
            
            self.board.clear()
            self.deck = Deck()

            # 🛡️ 【絶対防衛線 2】変数のクリーンリセット。ここでも0ptのプレイヤーが混ざる余地を完全に排除
            for p in self.players: 
                p.reset_for_new_game()
                if p.chips <= 0:
                    p.is_busted = True
                    p.status = HandStatus.FOLDED
            
            living_players = [p for p in self.players if not p.is_busted]

            if self.dealer_idx == -1:
                idx_in_actives = 0
            else:
                # 生存者の中から前回のディーラーの次の位置を正しく探す
                last_d_candidates = [p for p in self.players if p.id == self.dealer_idx]
                if last_d_candidates and last_d_candidates[0] in living_players:
                    idx_in_actives = (living_players.index(last_d_candidates[0]) + 1) % len(living_players)
                else:
                    idx_in_actives = 0 % len(living_players)
            
            self.dealer_idx = living_players[idx_in_actives].id
            num_living = len(living_players)

            if num_living == 2: 
                sb_p = living_players[idx_in_actives]
                bb_p = living_players[(idx_in_actives + 1) % num_living]
            else:
                sb_p = living_players[(idx_in_actives + 1) % num_living]
                bb_p = living_players[(idx_in_actives + 2) % num_living]

            # 💡 ブラインド徴収。すでに上のフェーズでchips=0の人間は除外されているため、必ず最小でも1以上のチップから徴収が始まります。
            sb_amnt = min(self.rules.SB, sb_p.chips)
            sb_p.chips -= sb_amnt
            sb_p.round_bet = sb_amnt 
            sb_p.game_bet = sb_amnt  
            if sb_p.chips == 0: 
                sb_p.status = HandStatus.ALL_IN if sb_amnt > 0 else HandStatus.FOLDED
                sb_p.acted = True 

            bb_amnt = min(self.rules.BB, bb_p.chips)
            bb_p.chips -= bb_amnt
            bb_p.round_bet = bb_amnt 
            bb_p.game_bet = bb_amnt  
            if bb_p.chips == 0: 
                bb_p.status = HandStatus.ALL_IN if bb_amnt > 0 else HandStatus.FOLDED
                bb_p.acted = True 

            print(f" 📢 【システム】{sb_p.name} がSB({sb_amnt}pt)を支払いました。")
            print(f" 📢 【システム】{bb_p.name} がBB({bb_amnt}pt)を支払いました。")

            self.verify_chip_integrity(f"第{games_count}戦・カード配布前")

            for p in living_players:
                if p.status == HandStatus.FOLDED:
                    continue
                p.hand = self.deck.draw(2)
                if self.debug_mode and not p.is_human:
                    print(f" [DEBUG] {p.name} の手札: {p.hand[0]}{p.hand[1]}")

            self.run_betting_round("プリフロップ")

            for phase in ["フロップ", "ターン", "リバー"]:
                survivors_count = sum(1 for p in self.players if p.status != HandStatus.FOLDED and not p.is_busted)
                
                if survivors_count > 1:
                    if (phase == "フロップ" and len(self.board) < 3) or (phase in ["ターン", "リバー"] and len(self.board) < 5):
                        self.board.extend(self.deck.draw(3 if phase == "フロップ" else 1))
                    
                    playable_count = sum(1 for p in self.players if p.can_make_action())
                    if playable_count >= 2:
                        self.run_betting_round(phase)

            survivors = [p for p in self.players if p.status != HandStatus.FOLDED and not p.is_busted]
            
            if len(survivors) == 1:
                winner = survivors[0]
                total_pot = sum(p.game_bet for p in self.players)
                winner.chips += total_pot
                print(f"\n全員がフォールドしたため、{winner.name} の不戦勝です！\n 💰 {total_pot}pt を獲得。")
                
                for p in self.players:
                    p.game_bet = 0
            else:
                self.draw_ui("ショーダウン")
                print("\n" + "=" * 70)
                print(" 🔥 [LOG] ショーダウン結果発表 🔥")
                print("=" * 70)
                for p in survivors:
                    score, name = evaluate_7_cards(p.hand + self.board)
                    p.score = score
                    p.hand_name = name
                    print(f" 🃏 {p.name:<6}: {p.hand[0]} {p.hand[1]} -> 【{name}】")
                print("----------------------------------------------------------------------")
                
                distribution_logs = self.pot_manager.distribute_pots(self.players)
                for log in distribution_logs:
                    print(log)
                print("======================================================================\n")
                
                for p in self.players:
                    p.game_bet = 0

            for p in living_players:
                if p.chips <= 0 and not p.is_busted:
                    p.chips = 0
                    p.is_busted = True
                    print(f"📢 【アナウンス】{p.name} が完全に破産（トビ）しました。")

            self.verify_chip_integrity(f"第{games_count}戦・配当完了後")

            next_living = [p for p in self.players if not p.is_busted]
            if not any(p.is_human for p in next_living) or (len(next_living) == 1 and next_living[0].is_human):
                continue

            cmd = self.safe_input("\n--- [Enter] で次のゲームへ / (q)で終了 --- ").strip().lower()
            if cmd == 'q': break


if __name__ == "__main__":
    game = TexasHoldemGame()
    game.start_game_loop()
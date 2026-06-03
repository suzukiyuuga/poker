import random
from collections import Counter
import itertools

# =====================================================================
# 1. 定数・基本データ定義セクション
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
    0: "ハイカード（役なし）"
}

# =====================================================================
# 2. クラス定義セクション
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

# =====================================================================
# 3. 役の判定・ドロー（期待値）判定ロジック
# =====================================================================
def check_straight(values):
    if len(values) != 5:
        return False, 0
    if values[0] - values[4] == 4:
        return True, values[0]
    if set(values) == {14, 5, 4, 3, 2}:
        return True, 5
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
    
    if is_flush and is_straight and straight_high == 14:
        return (9, 14), HAND_NAMES[9]
    if is_flush and is_straight:
        high_card_str = VALUE_TO_RANK[straight_high]
        return (8, straight_high), f"{high_card_str} ハイ・ストレートフラッシュ"
    if count_pairs[0][0] == 4:
        quad_val = count_pairs[0][1]
        kicker_val = count_pairs[1][1]
        return (7, quad_val, kicker_val), f"{VALUE_TO_RANK[quad_val]}のフォーカード"
    if count_pairs[0][0] == 3 and count_pairs[1][0] == 2:
        trips_val = count_pairs[0][1]
        pair_val = count_pairs[1][1]
        return (6, trips_val, pair_val), f"{VALUE_TO_RANK[trips_val]}と{VALUE_TO_RANK[pair_val]}のフルハウス"
    if is_flush:
        return (5, tuple(values)), f"{VALUE_TO_RANK[values[0]]} ハイ・フラッシュ"
    if is_straight:
        high_card_str = VALUE_TO_RANK[straight_high]
        return (4, straight_high), f"{high_card_str} ハイ・ストレート"
    if count_pairs[0][0] == 3:
        trips_val = count_pairs[0][1]
        kicker1 = count_pairs[1][1]
        kicker2 = count_pairs[2][1]
        return (3, trips_val, kicker1, kicker2), f"{VALUE_TO_RANK[trips_val]}のスリーカード"
    if count_pairs[0][0] == 2 and count_pairs[1][0] == 2:
        high_pair = count_pairs[0][1]
        low_pair = count_pairs[1][1]
        kicker = count_pairs[2][1]
        return (2, high_pair, low_pair, kicker), f"{VALUE_TO_RANK[high_pair]}と{VALUE_TO_RANK[low_pair]}のツーペア"
    if count_pairs[0][0] == 2:
        pair_val = count_pairs[0][1]
        kicker1 = count_pairs[1][1]
        kicker2 = count_pairs[2][1]
        kicker3 = count_pairs[3][1]
        return (1, pair_val, kicker1, kicker2, kicker3), f"{VALUE_TO_RANK[pair_val]}のワンペア"
        
    return (0, tuple(values)), f"{VALUE_TO_RANK[values[0]]}ハイ（役なし）"

def evaluate_7_cards(cards):
    best_score = (-1,)
    best_hand_name = "ハイカード"
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        if score > best_score:
            best_score = score
            best_hand_name = name
    return best_score, best_hand_name

def check_draw_opportunity(cards):
    if len(cards) < 4:
        return False
    suits = [c.suit for c in cards]
    if any(count >= 4 for count in Counter(suits).values()):
        return True
    values = set(c.value for c in cards)
    if 14 in values:
        values.add(1)
    sorted_vals = sorted(list(values))
    for i in range(len(sorted_vals) - 3):
        if sorted_vals[i+3] - sorted_vals[i] <= 4:
            return True
    return False

# =====================================================================
# 4. CPU思考エンジン・セクション
# =====================================================================
def cpu_decision(cpu_cards, board, to_call, cpu_chips, current_pot):
    all_cards = cpu_cards + board
    score_idx = evaluate_7_cards(all_cards)[0][0] if len(all_cards) >= 5 else 0
    is_draw = check_draw_opportunity(all_cards)
    
    if to_call == 0:
        # 相手からベットされていない時（チェックかベットの選択）
        if score_idx >= 2 or (random.random() < 0.10):
            bet_size = min(40, cpu_chips)
            return 2, bet_size
        return 1, 0
    else:
        # 相手からベット（またはレイズ）されている時
        if score_idx >= 3:
            if cpu_chips > to_call and random.random() < 0.4:
                raise_size = min(to_call + 40, cpu_chips)
                return 2, raise_size
            return 1, 0
            
        if score_idx in [1, 2]:
            if score_idx == 1 and to_call > 150 and random.random() < 0.30:
                return 3, 0
            return 1, 0
            
        if score_idx == 0:
            if is_draw and to_call <= 100:
                return 1, 0
            if to_call <= 30:
                return 1, 0
            if random.random() < 0.02 and cpu_chips >= to_call + 40:
                return 2, to_call + 40
            return 3, 0
            
        return 1, 0

# =====================================================================
# 5. ベッティングラウンド・セクション
# =====================================================================
def betting_round(player, cpu, board, round_name, pot, dealer, total_game_bets):
    print(f"\n--- {round_name} ベッティングラウンド ---")
    if board:
        print(f"場札: {' '.join(map(str, board))}")
    print(f"あなたの手札: {player['hand'][0]} {player['hand'][1]}")
    
    # このラウンド内だけの各プレイヤーのベット額を管理するローカル変数
    # プリフロップ時のみ、ブラインド（全ゲーム累計賭け金）を引き継ぐ
    if round_name == "プリフロップ":
        round_bets = {0: total_game_bets[0], 1: total_game_bets[1]}
    else:
        round_bets = {0: 0, 1: 0}
        
    highest_bet = max(round_bets[0], round_bets[1])
    
    if round_name == "プリフロップ":
        current_actor = 0 if dealer == 0 else 1
    else:
        current_actor = 1 if dealer == 0 else 0
        
    acted = {0: False, 1: False}
    active = {0: True, 1: True}
    
    while True:
        if not active[0] or not active[1]:
            break
            
        if (player["chips"] == 0 or cpu["chips"] == 0) and round_bets[0] == round_bets[1]:
            break
        if (player["chips"] == 0 and round_bets[0] <= round_bets[1]) or (cpu["chips"] == 0 and round_bets[1] <= round_bets[0]):
            if acted[0] and acted[1]:
                break
                
        if acted[0] and acted[1] and round_bets[0] == round_bets[1]:
            break
            
        to_call = highest_bet - round_bets[current_actor]
        
        print(f"[ポット総額: {pot} チップ] (現在のこのラウンドの賭け金 -> あなた: {round_bets[0]} | CPU: {round_bets[1]})")
        
        # -----------------------------------------------------------------
        # プレイヤーの番
        # -----------------------------------------------------------------
        if current_actor == 0:
            if player["chips"] == 0:
                acted[0] = True
                current_actor = 1
                continue
                
            print(f"【あなたの番】（所持: {player['chips']}, コールに必要な額: {to_call}）")
            
            while True:
                action = input("アクション（1: コール/チェック, 2: ベット/レイズ, 3: フォールド）: ").strip()
                if action in ["1", "2", "3"]:
                    break
                print("無効な入力です。'1', '2', '3' のいずれかを入力してください。")
            
            if action == "1":
                call_amnt = min(to_call, player["chips"])
                player["chips"] -= call_amnt
                round_bets[0] += call_amnt
                total_game_bets[0] += call_amnt
                pot += call_amnt
                print(f"あなた: {'チェック' if call_amnt == 0 else f'{call_amnt}チップでコール'}")
                acted[0] = True
                current_actor = 1
                
            elif action == "2":
                action_title = "ベット" if highest_bet == 0 else "レイズ"
                
                # 最低ベット/レイズ額の計算
                if highest_bet == 0:
                    min_round_total_needed = 20
                else:
                    min_round_total_needed = highest_bet + max(20, highest_bet)
                
                min_player_input = min_round_total_needed - round_bets[0]
                max_player_input = player["chips"]
                
                if max_player_input <= to_call:
                    print("チップが足りないためベット/レイズできません。コールするかフォールドしてください。")
                    continue

                print(f"いくら賭けますか？（現在のチップから追加する額を入力してください）")
                
                while True:
                    try:
                        r_input = input(f"追加する額 ({min_player_input} 〜 {max_player_input}): ")
                        raise_val = int(r_input)
                        if min_player_input <= raise_val <= max_player_input: 
                            break
                        print("無効な額です。指定された範囲内で入力してください。")
                    except ValueError:
                        print("数字で入力してください。")
                        
                player["chips"] -= raise_val
                round_bets[0] += raise_val
                total_game_bets[0] += raise_val
                pot += raise_val
                highest_bet = max(highest_bet, round_bets[0])
                
                is_all_in = "（オールイン！）" if player['chips'] == 0 else ""
                print(f"あなた: 合計{round_bets[0]}チップに{action_title}！{is_all_in}")
                acted[0] = True
                acted[1] = False 
                current_actor = 1
                
            elif action == "3":
                print("あなた: フォールドしました。")
                active[0] = False
                
        # -----------------------------------------------------------------
        # CPUの番
        # -----------------------------------------------------------------
        else:
            if cpu["chips"] == 0:
                acted[1] = True
                current_actor = 0
                continue
                
            cpu_action, cpu_raise_val = cpu_decision(cpu["hand"], board, to_call, cpu["chips"], pot)
            
            if cpu_action == 2 and cpu["chips"] <= to_call:
                cpu_action = 1
                
            if cpu_action == 1: 
                call_amnt = min(to_call, cpu["chips"])
                cpu["chips"] -= call_amnt
                round_bets[1] += call_amnt
                total_game_bets[1] += call_amnt
                pot += call_amnt
                print(f"\n【CPUの番】\nCPU: {'チェックしました。' if call_amnt == 0 else f'{call_amnt}チップでコールしました。'}{'（オールイン！）' if cpu['chips']==0 else ''}")
                acted[1] = True
                current_actor = 0
                
            elif cpu_action == 2: 
                action_title = "ベット" if highest_bet == 0 else "レイズ"
                
                if highest_bet == 0:
                    actual_add = max(20, cpu_raise_val)
                else:
                    min_increment = max(20, highest_bet)
                    actual_add = max(to_call + min_increment, cpu_raise_val)
                    
                actual_add = min(actual_add, cpu["chips"])
                
                cpu["chips"] -= actual_add
                round_bets[1] += actual_add
                total_game_bets[1] += actual_add
                pot += actual_add
                highest_bet = max(highest_bet, round_bets[1])
                
                is_all_in = "（オールイン！）" if cpu['chips'] == 0 else ""
                print(f"\n【CPUの番】\nCPU: 合計{round_bets[1]}チップに{action_title}しました！{is_all_in}")
                acted[1] = True
                acted[0] = False
                current_actor = 0
                
            elif cpu_action == 3: 
                print(f"\n【CPUの番】\nCPU: フォールドしました。")
                active[1] = False
                    
    return pot, active[0], active[1]

# =====================================================================
# 6. ゲーム全体管理セクション
# =====================================================================
def play_game():
    print("=========================================")
    print("♠♥♦♣ ULTIMATE TEXAS HOLD'EM POKER ♣♦♥♠")
    print("=========================================")
    
    while True:
        db_input = input("デバッグモード（相手の手札を常時表示）にしますか？ (y/n): ").strip().lower()
        if db_input in ['y', 'n']:
            break
        print("無効な入力です。'y' または 'n' を入力してください。")
        
    debug_mode = (db_input == 'y')
    
    player, cpu = {"chips": 1000, "hand": []}, {"chips": 1000, "hand": []}
    games_count = 0
    
    while player["chips"] > 0 and cpu["chips"] > 0:
        games_count += 1
        print(f"\n=========================================")
        print(f"★ 第 {games_count} 回戦 スタート ★")
        print(f"あなたのチップ: {player['chips']} | CPUのチップ: {cpu['chips']}")
        print("=========================================")
        
        deck = Deck()
        board = []
        dealer = games_count % 2 
        
        # 1ゲーム全体の累計賭け金を記録する変数
        total_game_bets = {0: 0, 1: 0}
        
        if dealer == 0:
            sb = min(10, player["chips"])
            bb = min(20, cpu["chips"])
            player["chips"] -= sb
            cpu["chips"] -= bb
            total_game_bets[0] += sb
            total_game_bets[1] += bb
            pot = sb + bb
            print("--- ブラインド（強制ベット）ポスト ---")
            print(f"あなたはスモールブラインド({sb})を支払いました。\nCPUはビッグブラインド({bb})を支払いました。")
        else:
            sb = min(10, cpu["chips"])
            bb = min(20, player["chips"])
            cpu["chips"] -= sb
            player["chips"] -= bb
            total_game_bets[0] += bb
            total_game_bets[1] += sb
            pot = sb + bb
            print("--- ブラインド（強制ベット）ポスト ---")
            print(f"CPUはスモールブラインド({sb})を支払いました。\nあなたはビッグブラインド({bb})を支払いました。")
            
        player["hand"] = deck.draw(2)
        cpu["hand"] = deck.draw(2)
        if debug_mode: 
            print(f"【DEBUG】CPUの手札: {cpu['hand'][0]} {cpu['hand'][1]}")
            
        p_active, c_active = True, True
        
        # 1. プリフロップ
        pot, p_active, c_active = betting_round(player, cpu, board, "プリフロップ", pot, dealer, total_game_bets)
        
        # 2. フロップ
        if p_active and c_active:
            board.extend(deck.draw(3))
            if player["chips"] > 0 or cpu["chips"] > 0:
                pot, p_active, c_active = betting_round(player, cpu, board, "フロップ", pot, dealer, total_game_bets)
                
        # 3. ターン
        if p_active and c_active:
            board.extend(deck.draw(1))
            if player["chips"] > 0 or cpu["chips"] > 0:
                pot, p_active, c_active = betting_round(player, cpu, board, "ターン", pot, dealer, total_game_bets)
                
        # 4. リバー
        if p_active and c_active:
            board.extend(deck.draw(1))
            if player["chips"] > 0 or cpu["chips"] > 0:
                pot, p_active, c_active = betting_round(player, cpu, board, "リバー", pot, dealer, total_game_bets)
            
        # --- 出しすぎたチップの自動返却ロジック ---
        if p_active and c_active:
            if total_game_bets[0] > total_game_bets[1]:
                returned = total_game_bets[0] - total_game_bets[1]
                player["chips"] += returned
                pot -= returned
                print(f"\n【システム】CPUの賭け金上限を超えていたため、あなたに差額 {returned} チップが返却されました。")
                total_game_bets[0] = total_game_bets[1]
            elif total_game_bets[1] > total_game_bets[0]:
                returned = total_game_bets[1] - total_game_bets[0]
                cpu["chips"] += returned
                pot -= returned
                print(f"\n【システム】あなたの賭け金上限を超えていたため、CPUに差額 {returned} チップが返却されました。")
                total_game_bets[1] = total_game_bets[0]

        # --- ショーダウン（勝敗判定） ---
        print("\n--- ショーダウン（勝敗判定） ---")
        if not p_active:
            print("あなたフォールドにより、CPUの勝ちです！")
            cpu["chips"] += pot
        elif not c_active:
            print("CPUフォールドにより、あなたの勝ちです！")
            player["chips"] += pot
        else:
            print(f"場札: {' '.join(map(str, board))}")
            print(f"あなた: {player['hand'][0]} {player['hand'][1]}")
            print(f"CPU  : {cpu['hand'][0]} {cpu['hand'][1]}")
            
            p_score, p_name = evaluate_7_cards(player["hand"] + board)
            c_score, c_name = evaluate_7_cards(cpu["hand"] + board)
            
            print(f"あなたの役: {p_name}")
            print(f"CPUの役  : {c_name}")
            
            if p_score > c_score:
                print(f"あなたの勝ち！ {pot} チップを獲得。")
                player["chips"] += pot
            elif c_score > p_score:
                print(f"CPUの勝ち！ {pot} チップを獲得。")
                cpu["chips"] += pot
            else:
                share = pot // 2
                remainder = pot % 2
                
                if remainder > 0:
                    if dealer == 0: 
                        player["chips"] += (share + remainder)
                        cpu["chips"] += share
                        print(f"引き分け（チョップ）！ 端数チップを考慮し、あなたに {share + remainder}、CPUに {share} 分配されました。")
                    else: 
                        player["chips"] += share
                        cpu["chips"] += (share + remainder)
                        print(f"引き分け（チョップ）！ 端数チップを考慮し、あなたに {share}、CPUに {share + remainder} 分配されました。")
                else:
                    player["chips"] += share
                    cpu["chips"] += share
                    print(f"引き分け（チョップ）！ チップを等分します（各 {share} チップ）。")
                
        if player["chips"] <= 0:
            print("\nあなたの破産です。ゲームオーバー！")
            break
        elif cpu["chips"] <= 0:
            print("\nCPUを破産させました！完全勝利です！")
            break
            
        should_break = False
        while True:
            next_game = input("\n次のゲームに進みますか？ (y/n): ").strip().lower()
            if next_game == 'y':
                break
            elif next_game == 'n':
                should_break = True
                break
            else:
                print("無効な入力です。'y' または 'n' を入力してください。")
                
        if should_break:
            print("ゲームを終了します。")
            break

if __name__ == "__main__":
    play_game()
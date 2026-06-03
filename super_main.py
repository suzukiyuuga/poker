import random
from collections import Counter
import itertools

# =====================================================================
# 1. 定数・基本データ定義セクション
# =====================================================================
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

# 各ランクの強さを数値化（Aが最高値の14、2が最低値の2）
RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}
# 数値からランク文字を逆引きするための辞書（表示用）
VALUE_TO_RANK = {v: r for r, v in RANK_VALUES.items()}

# 役の強さの定義（数値が大きいほど強い）
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
# 2. クラス定義セクション（カードとデッキの管理）
# =====================================================================
class Card:
    """トランプのカード1枚を表すクラス"""
    def __init__(self, suit, rank):
        self.suit = suit        # スート（"♠", "♥" など）
        self.rank = rank        # ランク文字列（"A", "K", "10" など）
        self.value = RANK_VALUES[rank] # 強さの数値（2 〜 14）

    def __repr__(self):
        # 画面表示時のフォーマット（例: [♠A]）
        return f"[{self.suit}{self.rank}]"

class Deck:
    """52枚のデッキ（山札）を管理するクラス"""
    def __init__(self):
        # 52枚のカードを生成してシャッフル
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)

    def draw(self, n):
        # 指定された枚数（n枚）だけデッキからカードを引く
        return [self.cards.pop() for _ in range(n)]

# =====================================================================
# 3. 役の判定ロジック・セクション
# =====================================================================
def check_straight(values):
    """
    5枚の数値リスト（降順ソート済み、重複なし）がストレートか判定する関数
    戻り値: (True/False, ストレートの一番高い数値)
    """
    if len(values) != 5:
        return False, 0
    
    # 通常のストレート判定（最高値と最低値の差が4であれば連続している）
    if values[0] - values[4] == 4:
        return True, values[0]
        
    # 特殊ルール：A, 5, 4, 3, 2 のストレート（ホイール）の判定
    if set(values) == {14, 5, 4, 3, 2}:
        return True, 5 # この場合の最上位カードは「5」として扱う
        
    return False, 0

def evaluate_5_cards(cards):
    """
    厳密に5枚のカードを評価する関数
    戻り値: (スコアタプル, 画面表示用の役名文字列)
    ※スコアタプルは Python の性質（左の要素から順に比較される）を利用し、
      役が同じでもキッカー（残りのカード）の強さで正確に勝敗を競えるように構成しています。
    """
    # 5枚の数値を強い順（降順）にソート
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    
    # フラッシュ判定（5枚のスートがすべて同じか）
    is_flush = len(set(suits)) == 1
    
    # 重複を排除した数値リスト（ストレート判定用）
    unique_values = sorted(list(set(values)), reverse=True)
    
    # ストレート判定
    is_straight, straight_high = False, 0
    if len(unique_values) == 5:
        is_straight, straight_high = check_straight(unique_values)
        if is_straight and straight_high == 5:
            # A,5,4,3,2 の場合は比較用に値を [5,4,3,2,1] に置き換える（Aを最弱の1として扱うため）
            values = [5, 4, 3, 2, 1]
            
    # 同じ数値が何枚あるかをカウント（ペアやスリーカードの判定用）
    counts = Counter(values)
    # 「出現回数（多い順） -> カードの数値（強い順）」でソート
    # 例：[Q, Q, Q, 2, 2] の場合、[(3, 12), (2, 2)] になる
    count_pairs = sorted([(count, val) for val, count in counts.items()], key=lambda x: (x[0], x[1]), reverse=True)
    
    # ----------------------------------------
    # 各役の判定（強い順にチェック）
    # ----------------------------------------
    
    # 1. ロイヤルストレートフラッシュ
    if is_flush and is_straight and straight_high == 14:
        return (9, 14), HAND_NAMES[9]
        
    # 2. ストレートフラッシュ
    if is_flush and is_straight:
        high_card_str = VALUE_TO_RANK[straight_high]
        return (8, straight_high), f"{high_card_str} ハイ・ストレートフラッシュ"
        
    # 3. フォーカード
    if count_pairs[0][0] == 4:
        quad_val = count_pairs[0][1]   # 4枚あるカードの数値
        kicker_val = count_pairs[1][1] # 残り1枚（キッカー）の数値
        return (7, quad_val, kicker_val), f"{VALUE_TO_RANK[quad_val]}のフォーカード"
        
    # 4. フルハウス
    if count_pairs[0][0] == 3 and count_pairs[1][0] == 2:
        trips_val = count_pairs[0][1] # 3枚あるカードの数値
        pair_val = count_pairs[1][1]  # 2枚あるカードの数値
        return (6, trips_val, pair_val), f"{VALUE_TO_RANK[trips_val]}と{VALUE_TO_RANK[pair_val]}のフルハウス"
        
    # 5. フラッシュ（同じ役なら5枚全ての強さを順に比較）
    if is_flush:
        return (5, tuple(values)), f"{VALUE_TO_RANK[values[0]]} ハイ・フラッシュ"
        
    # 6. ストレート
    if is_straight:
        high_card_str = VALUE_TO_RANK[straight_high]
        return (4, straight_high), f"{high_card_str} ハイ・ストレート"
        
    # 7. スリーカード
    if count_pairs[0][0] == 3:
        trips_val = count_pairs[0][1] # 3枚あるカードの数値
        kicker1 = count_pairs[1][1]   # キッカー1（強い方）
        kicker2 = count_pairs[2][1]   # キッカー2（弱い方）
        return (3, trips_val, kicker1, kicker2), f"{VALUE_TO_RANK[trips_val]}のスリーカード"
        
    # 8. ツーペア（2つのペアの強さ + 残り1枚のキッカーまで厳密に比較）
    if count_pairs[0][0] == 2 and count_pairs[1][0] == 2:
        high_pair = count_pairs[0][1] # 高い方のペアの数値
        low_pair = count_pairs[1][1]  # 低い方のペアの数値
        kicker = count_pairs[2][1]    # 残り1枚のキッカーの数値
        return (2, high_pair, low_pair, kicker), f"{VALUE_TO_RANK[high_pair]}と{VALUE_TO_RANK[low_pair]}のツーペア"
        
    # 9. ワンペア（ペアの数値 + 残り3枚のキッカーまで全てを比較対象にする）
    if count_pairs[0][0] == 2:
        pair_val = count_pairs[0][1] # ペアの数値
        kicker1 = count_pairs[1][1]  # キッカー1
        kicker2 = count_pairs[2][1]  # キッカー2
        kicker3 = count_pairs[3][1]  # キッカー3
        return (1, pair_val, kicker1, kicker2, kicker3), f"{VALUE_TO_RANK[pair_val]}のワンペア"
        
    # 10. ハイカード（役なし：5枚すべてのカードを強い順に比較）
    return (0, tuple(values)), f"{VALUE_TO_RANK[values[0]]}ハイ（役なし）"

def evaluate_7_cards(cards):
    """7枚のカード（手札2枚＋場札5枚）から、最も強くなる5枚の組み合わせを選び出す関数"""
    best_score = (-1,)
    best_hand_name = "ハイカード"
    
    # 7枚から5枚を選ぶ全組み合わせ（21通り）をループ処理
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        # より強いスコアが見つかれば更新
        if score > best_score:
            best_score = score
            best_hand_name = name
            
    return best_score, best_hand_name

# =====================================================================
# 4. ベッティングラウンド・セクション（ゲームの進行・賭けのやり取り）
# =====================================================================
def betting_round(player, cpu, board, round_name, pot, dealer):
    """各ラウンド（プリフロップ、フロップなど）の賭けチップ処理を行う関数"""
    print(f"\n--- {round_name} ベッティングラウンド ---")
    if board:
        print(f"場札: {' '.join(map(str, board))}")
    print(f"現在のポット: {pot} チップ")
    print(f"あなたの手札: {player['hand'][0]} {player['hand'][1]}")
    
    highest_bet = 0  # このラウンド内での最高ベット額
    bets = {0: 0, 1: 0}  # 0: プレイヤーの賭け額, 1: CPUの賭け額
    
    # プリフロップの場合のみ、ブラインド（強制ベット）を初期値として設定
    if round_name == "プリフロップ":
        if dealer == 0:
            bets[0], bets[1] = 10, 20  # プレイヤーがSB、CPUがBB
            highest_bet = 20
        else:
            bets[0], bets[1] = 20, 10  # CPUがSB、プレイヤーがBB
            highest_bet = 20

    # アクションを起こす順番の決定（SB側から先に動く）
    current_actor = 0 if dealer == 0 else 1
    acted = {0: False, 1: False}   # それぞれが一度でもアクションを完了したか
    active = {0: True, 1: True}     # まだフォールドせず勝負に残っているか
    
    # ベッティングのメインループ
    while True:
        # どちらかがフォールドした場合は即終了
        if not active[0] or not active[1]:
            break
            
        # オールイン（チップ0）が発生しており、賭け金が釣り合っていれば終了
        if (player["chips"] == 0 or cpu["chips"] == 0):
            if bets[0] >= bets[1] and cpu["chips"] == 0:
                break
            if bets[1] >= bets[0] and player["chips"] == 0:
                break
                
        # お互いが最低1回は行動し、かつ賭け金が一致していればラウンド終了
        if acted[0] and acted[1] and bets[0] == bets[1]:
            break
            
        # コール（追いつく）するために必要な追加チップ額
        to_call = highest_bet - bets[current_actor]
        
        # ----------------------------------------
        # プレイヤーのターン
        # ----------------------------------------
        if current_actor == 0:
            if player["chips"] == 0:  # すでにオールインしている場合はパス
                acted[0] = True
                current_actor = 1
                continue
                
            print(f"\n【あなたの番】（所持: {player['chips']}, コールに必要な額: {to_call}）")
            
            # 入力ガード機能：1, 2, 3 以外は何度でも再入力を求める
            while True:
                action = input("アクション（1: コール/チェック, 2: ベット/レイズ, 3: フォールド）: ").strip()
                if action in ["1", "2", "3"]:
                    break
                print("無効な入力です。'1', '2', '3' のいずれかを入力してください。")
            
            # 1: コール または チェック
            if action == "1":
                call_amnt = min(to_call, player["chips"]) # 所持金を超えない範囲で支払う
                player["chips"] -= call_amnt
                bets[0] += call_amnt
                pot += call_amnt
                print(f"あなた: {'チェック' if call_amnt == 0 else f'{call_amnt}チップでコール'}")
                acted[0] = True
                current_actor = 1
                
            # 2: ベット または レイズ
            elif action == "2":
                # 賭けられる上限額の計算（相手の所持金＋現在の賭け金の差額が上限）
                max_raise = min(player["chips"], cpu["chips"] + bets[1] - bets[0])
                
                if max_raise <= 0 or max_raise < to_call:
                    print("相手がオールインしているため、これ以上レイズできません。コール（チェック）します。")
                    call_amnt = min(to_call, player["chips"])
                    player["chips"] -= call_amnt
                    bets[0] += call_amnt
                    pot += call_amnt
                    acted[0] = True
                    current_actor = 1
                    continue
                    
                # 最低レイズ額は「コールに必要な額 + 20」
                min_raise = min(to_call + 20, max_raise)
                
                # レイズ額の数値入力バリデーション
                while True:
                    try:
                        r_input = input(f"いくら賭けますか？ ({min_raise}〜{max_raise}): ")
                        raise_val = int(r_input)
                        if min_raise <= raise_val <= max_raise: 
                            break
                        print("無効な額です。")
                    except ValueError:
                        print("数字で入力してください。")
                        
                player["chips"] -= raise_val
                bets[0] += raise_val
                pot += raise_val
                highest_bet = max(highest_bet, bets[0])
                print(f"あなた: {bets[0]}チップにレイズ！")
                acted[0] = True
                acted[1] = False # レイズされたので相手は再度アクションが必要
                current_actor = 1
                
            # 3: フォールド
            elif action == "3":
                print("あなた: フォールドしました。")
                active[0] = False
                
        # ----------------------------------------
        # CPUのターン（シンプルなAIロジック）
        # ----------------------------------------
        else:
            if cpu["chips"] == 0:  # すでにオールインしている場合はパス
                acted[1] = True
                current_actor = 0
                continue
                
            # CPUの現時点での役の強さを計算（フロップ以降のみ）
            all_cards = cpu["hand"] + board
            score_idx = evaluate_7_cards(all_cards)[0][0] if len(all_cards) >= 5 else 0
            
            # パス（チェック）できる状態のとき
            if to_call == 0:
                # ツーペア以上の強い役があり、チップに余裕があれば40チップベット
                if score_idx >= 2 and cpu["chips"] >= 40:
                    bet_val = min(40, cpu["chips"])
                    cpu["chips"] -= bet_val
                    bets[1] += bet_val
                    pot += bet_val
                    highest_bet = max(highest_bet, bets[1])
                    print(f"\n【CPUの番】\nCPU: {bets[1]}チップにベットしました！")
                    acted[1] = True
                    acted[0] = False # ベットされたのでプレイヤーは再度アクションが必要
                    current_actor = 0
                else:
                    print(f"\n【CPUの番】\nCPU: チェックしました。")
                    acted[1] = True
                    current_actor = 0
            # 相手（プレイヤー）がベット・レイズしてきたとき
            else:
                # 役がなくて相手の賭け金が高い(60超)場合、約90%の確率でフォールド
                if score_idx == 0 and to_call > 60 and random.random() > 0.1:
                    print(f"\n【CPUの番】\nCPU: フォールドしました。")
                    active[1] = False
                # それ以外はコールして勝負を続行
                else:
                    call_amnt = min(to_call, cpu["chips"])
                    cpu["chips"] -= call_amnt
                    bets[1] += call_amnt
                    pot += call_amnt
                    print(f"\n【CPUの番】\nCPU: {call_amnt}チップでコールしました。{'（オールイン！）' if cpu['chips']==0 else ''}")
                    acted[1] = True
                    current_actor = 0
                    
    return pot, active[0], active[1]

# =====================================================================
# 5. ゲーム全体管理セクション（メインループ）
# =====================================================================
def play_game():
    """ゲーム全体の流れを制御するメイン関数"""
    print("=========================================")
    print("♠♥♦♣ ULTIMATE TEXAS HOLD'EM POKER ♣♦♥♠")
    print("=========================================")
    
    # デバッグモード選択のバリデーション
    while True:
        db_input = input("デバッグモード（相手の手札を常時表示）にしますか？ (y/n): ").strip().lower()
        if db_input in ['y', 'n']:
            break
        print("無効な入力です。'y' または 'n' を入力してください。")
        
    debug_mode = (db_input == 'y')
    
    # プレイヤーとCPUの初期チップを1000に設定
    player, cpu = {"chips": 1000, "hand": []}, {"chips": 1000, "hand": []}
    games_count = 0
    
    # どちらかのチップが尽きるまでゲーム（回戦）をループ
    while player["chips"] > 0 and cpu["chips"] > 0:
        games_count += 1
        print(f"\n=========================================")
        print(f"★ 第 {games_count} 回戦 スタート ★")
        print(f"あなたのチップ: {player['chips']} | CPUのチップ: {cpu['chips']}")
        print("=========================================")
        
        deck = Deck()   # 新しい山札を用意
        board = []      # コミュニティカード（場札）を初期化
        dealer = games_count % 2 # 親（ディーラーボタン）を交互に交代
        
        # --- ブラインド（強制ベット）の徴収 ---
        if dealer == 0:
            sb = min(10, player["chips"])
            bb = min(20, cpu["chips"])
            player["chips"] -= sb
            cpu["chips"] -= bb
            pot = sb + bb
            print("--- ブラインド（強制ベット）ポスト ---")
            print(f"あなたはスモールブラインド({sb})を支払いました。\nCPUはビッグブラインド({bb})を支払いました。")
        else:
            sb = min(10, cpu["chips"])
            bb = min(20, player["chips"])
            cpu["chips"] -= sb
            player["chips"] -= bb
            pot = sb + bb
            print("--- ブラインド（強制ベット）ポスト ---")
            print(f"CPUはスモールブラインド({sb})を支払いました。\nあなたはビッグブラインド({bb})を支払いました。")
            
        # 手札を2枚ずつ配る
        player["hand"] = deck.draw(2)
        cpu["hand"] = deck.draw(2)
        if debug_mode: 
            print(f"【DEBUG】CPUの手札: {cpu['hand'][0]} {cpu['hand'][1]}")
            
        p_active, c_active = True, True # 参加フラグの初期化
        
        # 1. プリフロップ・ラウンド（手札2枚のみの状態）
        pot, p_active, c_active = betting_round(player, cpu, board, "プリフロップ", pot, dealer)
        
        # 2. フロップ・ラウンド（場札を3枚出す）
        if p_active and c_active:
            board.extend(deck.draw(3))
            if player["chips"] > 0 and cpu["chips"] > 0:
                pot, p_active, c_active = betting_round(player, cpu, board, "フロップ", pot, dealer)
                
        # 3. ターン・ラウンド（場札を1枚追加して計4枚）
        if p_active and c_active:
            board.extend(deck.draw(1))
            if player["chips"] > 0 and cpu["chips"] > 0:
                pot, p_active, c_active = betting_round(player, cpu, board, "ターン", pot, dealer)
                
        # 4. リバー・ラウンド（場札を最後の1枚追加して計5枚）
        if p_active and c_active:
            board.extend(deck.draw(1))
            if player["chips"] > 0 and cpu["chips"] > 0:
                pot, p_active, c_active = betting_round(player, cpu, board, "リバー", pot, dealer)
            
        # --- 勝敗判定・ショーダウンセクション ---
        print("\n--- ショーダウン（勝敗判定） ---")
        if not p_active:
            print("あなたフォールドにより、CPUの勝ちです！")
            cpu["chips"] += pot
        elif not c_active:
            print("CPUフォールドにより、あなたの勝ちです！")
            player["chips"] += pot
        else:
            # 双方が残っている場合は役を厳密に比較
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
                # キッカーまで完全に同じだった場合はチョップ（引き分け）
                print(f"引き分け（チョップ）！ チップを等分します。")
                player["chips"] += pot // 2
                cpu["chips"] += pot // 2
                
        # --- 破産（決着）判定 ---
        if player["chips"] <= 0:
            print("\nあなたの破産です。ゲームオーバー！")
            break
        elif cpu["chips"] <= 0:
            print("\nCPUを破産させました！完全勝利です！")
            break
            
        # 次の対戦への移行確認（入力ガード付き）
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

# プログラムのエントリーポイント
if __name__ == "__main__":
    play_game()
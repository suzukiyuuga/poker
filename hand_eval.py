# hand_eval.py 役を判定する機構を循環インポートを回避するために外部に移動した
from collections import Counter
import itertools

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

def evaluate_7_cards(cards):
    def check_straight(values):
        if len(values) != 5:
            return False, 0
        if values[0] - values[4] == 4:
            return True, values[0]
        if set(values) == {14, 5, 4, 3, 2}:
            return True, 5
        return False, 0

    def get_display_rank(five_cards, value):
        """
        five_cards: list of Card objects (with .value and .display_rank)
        value: integer card value (2..14)
        戻り値: 表示用の display_rank を文字列で返す（見つからなければ VALUE_TO_RANK[value] を返す）
        """
        # まず同じ value を持つカードを探す（display_rank が存在するはず）
        for c in five_cards:
            if c.value == value:
                return str(c.display_rank)
        # フォールバック: value を元にランク表記を返す（安全策）
        return VALUE_TO_RANK.get(value, str(value))

    def evaluate_5_cards(five_cards):
        values = sorted([c.value for c in five_cards], reverse=True)
        suits = [c.suit for c in five_cards]
        is_flush = len(set(suits)) == 1

        unique_values = sorted(list(set(values)), reverse=True)
        is_straight, straight_high = False, 0
        if len(unique_values) == 5:
            is_straight, straight_high = check_straight(unique_values)
            if is_straight and straight_high == 5:
                # A-2-3-4-5 の特殊扱いで表示上は最小ストレート（ハイは 5）
                values = [5, 4, 3, 2, 1]

        counts = Counter(values)
        count_pairs = sorted(
            [(count, val) for val, count in counts.items()],
            key=lambda x: (x[0], x[1]),
            reverse=True
        )

        # 役名の表示は display_rank を使う（内部 value ではなく）
        if is_flush and is_straight and straight_high == 14:
            # ロイヤルは固定名
            return (9, 14), HAND_NAMES[9]
        if is_flush and is_straight:
            disp = get_display_rank(five_cards, straight_high)
            return (8, straight_high), f"{disp}ハイ・ストレートフラッシュ"
        if count_pairs[0][0] == 4:
            quad_val = count_pairs[0][1]
            kicker_val = count_pairs[1][1]
            disp_quad = get_display_rank(five_cards, quad_val)
            disp_kicker = get_display_rank(five_cards, kicker_val)
            return (7, quad_val, kicker_val), f"{disp_quad}のフォーカード"
        if count_pairs[0][0] == 3 and count_pairs[1][0] == 2:
            trip_val = count_pairs[0][1]
            pair_val = count_pairs[1][1]
            disp_trip = get_display_rank(five_cards, trip_val)
            disp_pair = get_display_rank(five_cards, pair_val)
            return (6, trip_val, pair_val), f"{disp_trip}と{disp_pair}のフルハウス"
        if is_flush:
            # フラッシュは最高位の display_rank を使う
            high_val = values[0]
            disp = get_display_rank(five_cards, high_val)
            return (5, tuple(values)), f"{disp}ハイ・フラッシュ"
        if is_straight:
            disp = get_display_rank(five_cards, straight_high)
            return (4, straight_high), f"{disp}ハイ・ストレート"
        if count_pairs[0][0] == 3:
            trip_val = count_pairs[0][1]
            kick1 = count_pairs[1][1]
            kick2 = count_pairs[2][1]
            disp_trip = get_display_rank(five_cards, trip_val)
            return (3, trip_val, kick1, kick2), f"{disp_trip}のスリーカード"
        if count_pairs[0][0] == 2 and count_pairs[1][0] == 2:
            high_pair = count_pairs[0][1]
            low_pair = count_pairs[1][1]
            kicker = count_pairs[2][1]
            disp_high = get_display_rank(five_cards, high_pair)
            disp_low = get_display_rank(five_cards, low_pair)
            return (2, high_pair, low_pair, kicker), f"{disp_high}と{disp_low}のツーペア"
        if count_pairs[0][0] == 2:
            pair_val = count_pairs[0][1]
            # 残りキッカーの値を順に取る
            kickers = [cp[1] for cp in count_pairs[1:]]
            disp_pair = get_display_rank(five_cards, pair_val)
            return (1, pair_val, kickers[0], kickers[1], kickers[2]), f"{disp_pair}のワンペア"
        # ハイカード
        high_val = values[0]
        disp_high = get_display_rank(five_cards, high_val)
        return (0, tuple(values)), f"{disp_high}ハイ"

    best_score = (-1,)
    best_hand_name = "ハイカード"
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        if score > best_score:
            best_score, best_hand_name = score, name
    return best_score, best_hand_name
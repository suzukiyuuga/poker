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

    def evaluate_5_cards(five_cards):
        values = sorted([c.value for c in five_cards], reverse=True)
        suits = [c.suit for c in five_cards]
        is_flush = len(set(suits)) == 1

        unique_values = sorted(list(set(values)), reverse=True)
        is_straight, straight_high = False, 0
        if len(unique_values) == 5:
            is_straight, straight_high = check_straight(unique_values)
            if is_straight and straight_high == 5:
                values = [5, 4, 3, 2, 1]

        counts = Counter(values)
        count_pairs = sorted(
            [(count, val) for val, count in counts.items()],
            key=lambda x: (x[0], x[1]),
            reverse=True
        )

        if is_flush and is_straight and straight_high == 14:
            return (9, 14), HAND_NAMES[9]
        if is_flush and is_straight:
            return (8, straight_high), f"{VALUE_TO_RANK[straight_high]}ハイ・ストレートフラッシュ"
        if count_pairs[0][0] == 4:
            return (7, count_pairs[0][1], count_pairs[1][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}のフォーカード"
        if count_pairs[0][0] == 3 and count_pairs[1][0] == 2:
            return (6, count_pairs[0][1], count_pairs[1][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}と{VALUE_TO_RANK[count_pairs[1][1]]}のフルハウス"
        if is_flush:
            return (5, tuple(values)), f"{VALUE_TO_RANK[values[0]]}ハイ・フラッシュ"
        if is_straight:
            return (4, straight_high), f"{VALUE_TO_RANK[straight_high]}ハイ・ストレート"
        if count_pairs[0][0] == 3:
            return (3, count_pairs[0][1], count_pairs[1][1], count_pairs[2][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}のスリーカード"
        if count_pairs[0][0] == 2 and count_pairs[1][0] == 2:
            return (2, count_pairs[0][1], count_pairs[1][1], count_pairs[2][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}と{VALUE_TO_RANK[count_pairs[1][1]]}のツーペア"
        if count_pairs[0][0] == 2:
            return (1, count_pairs[0][1], count_pairs[1][1], count_pairs[2][1], count_pairs[3][1]), f"{VALUE_TO_RANK[count_pairs[0][1]]}のワンペア"
        return (0, tuple(values)), f"{VALUE_TO_RANK[values[0]]}ハイ"

    best_score = (-1,)
    best_hand_name = "ハイカード"
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        if score > best_score:
            best_score, best_hand_name = score, name
    return best_score, best_hand_name
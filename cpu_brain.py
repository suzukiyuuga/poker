import random
from collections import Counter
from hand_eval import evaluate_7_cards


def decide_cpu_action(room, cpu_player):
    """
    room: OnlinePokerRoom
    cpu_player: Player
    戻り値: (act, amount)
      act    : "call" / "raise" / "fold"
      amount : handle_action に渡す追加支払い額
    """
    to_call = min(room.highest_bet - cpu_player.round_bet, cpu_player.chips)

    # プリフロップ / ポストフロップで評価を分ける
    if len(room.board) == 0:
        strength = evaluate_preflop_structure(cpu_player.hand)
    else:
        strength = evaluate_postflop_structure(cpu_player.hand, room.board)

    # コール負担が重いときは弱気に補正
    stack_before_call = max(cpu_player.chips, 1)
    call_ratio = to_call / stack_before_call

    adjusted = strength
    if call_ratio >= 0.5:
        adjusted -= 25
    elif call_ratio >= 0.3:
        adjusted -= 15
    elif call_ratio >= 0.15:
        adjusted -= 8

    adjusted += random.randint(-6, 6)
    adjusted = max(0, min(adjusted, 100))

    # --- 行動決定 ---
    # チェック可能
    if to_call == 0:
        if adjusted >= 78 and cpu_player.chips > 0:
            if random.random() < 0.55:
                raise_amount = pick_cpu_raise_amount(room, cpu_player, adjusted, as_open=True)
                if raise_amount is not None:
                    return "raise", raise_amount
        return "call", 0

    # コールが必要
    if random.random() < 0.01:#確率で脳死コール
        return "call", to_call


    if adjusted >= 82:#以下合理的判断
        if random.random() < 0.55:
            raise_amount = pick_cpu_raise_amount(room, cpu_player, adjusted, as_open=False)
            if raise_amount is not None:
                return "raise", raise_amount
        return "call", to_call

    if adjusted >= 52:
        return "call", to_call

    if adjusted >= 35:
        if call_ratio <= 0.12 and random.random() < 0.65:
            return "call", to_call
        return "fold", 0

    if call_ratio <= 0.05 and random.random() < 0.15:
        return "call", to_call

    return "fold", 0


def evaluate_preflop_structure(hand):
    """
    hand: [Card, Card]
    絶対ランクの高さではなく、
    ペア・スーテッド・連結性だけで評価する。
    """
    c1, c2 = hand
    v1, v2 = c1.value, c2.value

    score = 25

    # ペア
    if v1 == v2:
        score += 55

    # スーテッド
    if c1.suit == c2.suit:
        score += 12

    gap = abs(v1 - v2)

    if gap == 1:
        score += 22
    elif gap == 2:
        score += 14
    elif gap == 3:
        score += 8
    elif gap == 4:
        score += 3

    if v1 != v2 and gap >= 6:
        score -= 8

    if c1.suit == c2.suit and gap <= 2:
        score += 10

    return max(0, min(score, 100))


def evaluate_postflop_structure(hand, board):
    """
    現在の役 + ドロー気配で評価する。
    """
    cards = hand + board
    if len(cards) < 5:
        return evaluate_preflop_structure(hand)

    score, hand_name = evaluate_7_cards(cards)
    hand_rank = score[0]

    total = 0

    base_by_hand = {
        0: 8,
        1: 35,
        2: 55,
        3: 68,
        4: 72,
        5: 75,
        6: 82,
        7: 90,
        8: 96,
        9: 100,
    }
    total += base_by_hand.get(hand_rank, 0)
    total += evaluate_draw_bonus(hand, board)
    total += evaluate_hole_card_involvement(hand, board)

    return max(0, min(total, 100))


def evaluate_draw_bonus(hand, board):
    cards = hand + board
    bonus = 0

    # フラッシュドロー
    suit_counts = Counter(c.suit for c in cards)
    max_suit = max(suit_counts.values())

    if len(board) < 5:
        if max_suit == 4:
            bonus += 18
        elif max_suit == 3 and len(board) == 3:
            bonus += 6

    # ストレートドロー
    values = sorted(set(c.value for c in cards))
    if 14 in values:
        values = sorted(set(values + [1]))

    best_window_count = 0
    value_set = set(values)
    for start in range(1, 11):
        window = set(range(start, start + 5))
        count = len(window & value_set)
        if count > best_window_count:
            best_window_count = count

    if len(board) < 5:
        if best_window_count >= 4:
            bonus += 16
        elif best_window_count == 3 and len(board) >= 3:
            bonus += 5

    return bonus


def evaluate_hole_card_involvement(hand, board):
    """
    手札がペア以上形成に絡んでいるかをざっくり評価
    """
    if len(board) < 3:
        return 0

    full_cards = hand + board
    hand_values = [c.value for c in hand]
    full_counter = Counter(c.value for c in full_cards)

    bonus = 0
    involved = 0

    for v in hand_values:
        if full_counter[v] >= 2:
            bonus += 5
            involved += 1

    if involved >= 2:
        bonus += 4

    return bonus


def pick_cpu_raise_amount(room, player, strength, as_open=False):
    """
    handle_action("raise", amount) に渡す amount は
    『今回追加で払う額』
    """
    highest_bet = room.highest_bet
    min_in = (highest_bet + room.min_raise_increment) - player.round_bet
    max_in = player.chips

    if max_in < min_in:
        return None

    if strength >= 90:
        target = min_in + int((max_in - min_in) * 0.75)
    elif strength >= 80:
        target = min_in + int((max_in - min_in) * 0.45)
    else:
        target = min_in + int((max_in - min_in) * 0.20)

    amount = random.randint(min_in, max(min_in, target))
    return min(amount, max_in)

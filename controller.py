import random
from collections import Counter
import itertools
from enum import Enum, auto

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
    def __init__(self, player_id, name, chips=1000, is_human=True):
        self.id = player_id
        self.name = name
        self.chips = chips          
        self.status = HandStatus.PLAYING
        self.is_busted = False      
        self.hand = []              
        self.game_bet = 0          
        self.round_bet = 0          
        self.acted = False          
        self.score = (-1,)          
        self.hand_name = ""        
        self.is_human = is_human  # CPU戦の判定用

    def reset_for_new_round(self):
        self.round_bet = 0
        if self.status == HandStatus.PLAYING:
            self.acted = False

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

class SidePot:
    def __init__(self, amount=0):
        self.amount = amount
        self.eligible_player_ids = []

class PotManager:
    def build_pots(self, players):
        pots = []
        active_bets = sorted(list(set(p.game_bet for p in players if p.game_bet > 0)))
        previous_level = 0
        for level in active_bets:
            current_pot = SidePot()
            pot_chips = 0
            for p in players:
                if p.game_bet >= level:
                    pot_chips += (level - previous_level)
                    if p.status != HandStatus.FOLDED and not p.is_busted:
                        current_pot.eligible_player_ids.append(p.id)
                else:
                    contribution = p.game_bet - previous_level
                    if contribution > 0:
                        pot_chips += contribution
            if pot_chips > 0:
                current_pot.amount = pot_chips
                if not current_pot.eligible_player_ids:
                    current_pot.eligible_player_ids = [pl.id for pl in players if pl.status != HandStatus.FOLDED and not pl.is_busted]
                pots.append(current_pot)
            previous_level = level
        return pots

    def distribute_pots(self, players):
        log_messages = []
        pots = self.build_pots(players)
        player_dict = {p.id: p for p in players}
        showdown_survivors = [p for p in players if p.status != HandStatus.FOLDED and not p.is_busted]
        
        for idx, pot in enumerate(pots):
            if pot.amount == 0: continue
            eligible_winners = [player_dict[pid] for pid in pot.eligible_player_ids if player_dict[pid].status != HandStatus.FOLDED and not player_dict[pid].is_busted]
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
            if distributed_sum != pot.amount:
                diff = pot.amount - distributed_sum
                winners[0].chips += diff
        return log_messages

def evaluate_7_cards(cards):
    def check_straight(values):
        if len(values) != 5: return False, 0
        if values[0] - values[4] == 4: return True, values[0]
        if set(values) == {14, 5, 4, 3, 2}: return True, 5
        return False, 0

    def evaluate_5_cards(five_cards):
        values = sorted([c.value for c in five_cards], reverse=True)
        suits = [c.suit for c in five_cards]
        is_flush = len(set(suits)) == 1
        unique_values = sorted(list(set(values)), reverse=True)
        is_straight, straight_high = False, 0
        if len(unique_values) == 5:
            is_straight, straight_high = check_straight(unique_values)
            if is_straight and straight_high == 5: values = [5, 4, 3, 2, 1]
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

    best_score = (-1,)
    best_hand_name = "ハイカード"
    for combo in itertools.combinations(cards, 5):
        score, name = evaluate_5_cards(list(combo))
        if score > best_score: best_score, best_hand_name = score, name
    return best_score, best_hand_name

class OnlinePokerRoom:
    def __init__(self, room_id, target_players=2):
        self.room_id = room_id
        self.players = []  
        self.board = []
        self.deck = None
        self.dealer_idx = -1
        self.action_logs = []
        self.chat_logs = []
        self.rules = GameStructure()
        self.pot_manager = PotManager()
        
        self.round_name = "待機中"
        self.highest_bet = 0
        self.min_raise_increment = 20
        self.list_cursor = 0
        self.current_turn_player_id = None
        self.game_started = False
        self.games_count = 0
        self.show_intermission = False
        
        self.target_players = target_players  # ★ 指定の開始人数

    def add_player(self, name, is_human=True):
        if len(self.players) >= self.target_players or self.game_started: return None
        p_id = len(self.players)
        p = Player(p_id, name, is_human=is_human)
        self.players.append(p)
        self.action_logs.append(f"📢 {name} が参加しました。({len(self.players)}/{self.target_players})")
        
        # ★ 特定の人数（目標人数）が集まった瞬間に開始
        if len(self.players) == self.target_players:
            self.start_new_game()
        return p_id

    def start_new_game(self):
        self.game_started = True
        self.show_intermission = False
        self.games_count += 1
        self.board.clear()
        self.deck = Deck()
        self.action_logs.append(f"🚨 ==================== 【 第 {self.games_count} 回 戦 開 始 】 ==================== 🚨")
        
        for p in self.players:
            p.reset_for_new_game()

        living = [p for p in self.players if not p.is_busted]
        if len(living) < 2:
            self.round_name = "ゲーム終了"
            return

        while True:
            self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
            if not self.players[self.dealer_idx].is_busted:
                break

        num_living = len(living)
        idx_in_actives = living.index(self.players[self.dealer_idx])
        
        if num_living == 2:
            sb_p = living[idx_in_actives]
            bb_p = living[(idx_in_actives + 1) % num_living]
        else:
            sb_p = living[(idx_in_actives + 1) % num_living]
            bb_p = living[(idx_in_actives + 2) % num_living]

        sb_amnt = min(self.rules.SB, sb_p.chips)
        sb_p.chips -= sb_amnt
        sb_p.round_bet = sb_amnt
        sb_p.game_bet = sb_amnt
        if sb_p.chips == 0: sb_p.status = HandStatus.ALL_IN

        bb_amnt = min(self.rules.BB, bb_p.chips)
        bb_p.chips -= bb_amnt
        bb_p.round_bet = bb_amnt
        bb_p.game_bet = bb_amnt
        if bb_p.chips == 0: bb_p.status = HandStatus.ALL_IN

        self.action_logs.append(f" 📢 【システム】{sb_p.name} がSB({sb_amnt}pt)を支払いました。")
        self.action_logs.append(f" 📢 【システム】{bb_p.name} がBB({bb_amnt}pt)を支払いました。")

        for p in self.players:
            if p.status != HandStatus.FOLDED and not p.is_busted:
                p.hand = self.deck.draw(2)

        self.start_betting_round("プリフロップ")

    def start_betting_round(self, r_name):
        self.round_name = r_name
        for p in self.players: p.reset_for_new_round()
        if r_name == "プリフロップ":
            for p in self.players: p.round_bet = p.game_bet
        
        self.highest_bet = max(p.round_bet for p in self.players)
        self.min_raise_increment = self.rules.MIN_RAISE_INCREMENT
        
        living = [p for p in self.players if not p.is_busted]
        num_living = len(living)
        idx_in_actives = living.index(self.players[self.dealer_idx])
        
        if num_living == 2:
            if r_name == "プリフロップ":
                start_p = living[idx_in_actives]
            else:
                start_p = living[(idx_in_actives + 1) % num_living]
        else:
            start_offset = 3 if r_name == "プリフロップ" else 1
            start_p = living[(idx_in_actives + start_offset) % num_living]
            
        self.list_cursor = self.players.index(start_p)
        self.next_turn()

    def next_turn(self):
        alive = sum(1 for p in self.players if p.status != HandStatus.FOLDED and not p.is_busted)
        playable = sum(1 for p in self.players if p.status == HandStatus.PLAYING and not p.is_busted)

        if alive <= 1 or playable == 0:
            self.advance_phase()
            return

        all_settled = True
        for p in self.players:
            if p.status == HandStatus.PLAYING and not p.is_busted:
                if not p.acted or p.round_bet != self.highest_bet:
                    all_settled = False
        if all_settled:
            self.advance_phase()
            return

        p = self.players[self.list_cursor]
        if p.status != HandStatus.PLAYING or p.is_busted:
            self.list_cursor = (self.list_cursor + 1) % len(self.players)
            self.next_turn()
            return

        self.current_turn_player_id = p.id
        
        # ★ もしCPUのターンなら、自動で即座に行動を決定するロジックを発動
        if not p.is_human:
            self.think_cpu_action(p)

    def think_cpu_action(self, cpu_player):
        """簡単なCPU思考ロジック"""
        to_call = min(self.highest_bet - cpu_player.round_bet, cpu_player.chips)
        # コール額が0ならチェック、それ以外なら確率でコールかフォールド
        if to_call == 0:
            act, amnt = "call", 0
        else:
            # 70%の確率でコール、30%でフォールド
            if random.random() < 0.7:
                act, amnt = "call", to_call
            else:
                act, amnt = "fold", 0
        self.handle_action(cpu_player.id, act, amnt)

    def handle_action(self, p_id, act_type, amount):
        if self.current_turn_player_id != p_id: return False
        p = self.players[p_id]
        
        if act_type == "call":
            p.chips -= amount
            p.round_bet += amount
            p.game_bet += amount
            if p.chips == 0: p.status = HandStatus.ALL_IN
            self.action_logs.append(f"{p.name}: {'チェック' if amount == 0 else f'{amount}ptでコール'}{'（All-in!）' if p.chips==0 else ''}")
            p.acted = True
        elif act_type == "raise":
            p.chips -= amount
            p.round_bet += amount
            p.game_bet += amount
            actual_increment = p.round_bet - self.highest_bet
            action_title = "ベット" if self.highest_bet == 0 else "レイズ"
            self.highest_bet = p.round_bet
            if actual_increment >= self.min_raise_increment:
                self.min_raise_increment = actual_increment
                for pl in self.players:
                    if pl.id != p.id and pl.status == HandStatus.PLAYING:
                        pl.acted = False
            if p.chips == 0: p.status = HandStatus.ALL_IN
            self.action_logs.append(f"{p.name}: 合計{p.round_bet}ptに{action_title}!{'（All-in!）' if p.chips==0 else ''}")
            p.acted = True
        elif act_type == "fold":
            p.status = HandStatus.FOLDED
            p.acted = True
            self.action_logs.append(f"{p.name}: フォールド")

        self.list_cursor = (self.list_cursor + 1) % len(self.players)
        self.next_turn()
        return True

    def advance_phase(self):
        self.current_turn_player_id = None
        survivors = sum(1 for p in self.players if p.status != HandStatus.FOLDED and not p.is_busted)
        
        if survivors <= 1:
            self.end_game()
            return

        phases = ["プリフロップ", "フロップ", "ターン", "リバー"]
        curr_idx = phases.index(self.round_name)
        if curr_idx == 3:
            self.end_game()
            return

        next_phase = phases[curr_idx + 1]
        if next_phase == "フロップ": self.board.extend(self.deck.draw(3))
        elif next_phase in ["ターン", "リバー"]: self.board.extend(self.deck.draw(1))
        
        self.start_betting_round(next_phase)

    def end_game(self):
        self.round_name = "結果発表"
        survivors = [p for p in self.players if p.status != HandStatus.FOLDED and not p.is_busted]
        
        if len(survivors) == 1:
            winner = survivors[0]
            total_pot = sum(p.game_bet for p in self.players)
            winner.chips += total_pot
            self.action_logs.append(f"全員がフォールドしたため、{winner.name} の不戦勝です！ 💰 {total_pot}pt を獲得。")
        else:
            self.action_logs.append("================= 最終結果 (Showdown) =================")
            for p in survivors:
                score, name = evaluate_7_cards(p.hand + self.board)
                p.score = score
                p.hand_name = name
                self.action_logs.append(f" 🃏 {p.name:<6}: {p.hand[0]} {p.hand[1]} -> 【{name}】")
            
            dist_logs = self.pot_manager.distribute_pots(self.players)
            self.action_logs.extend(dist_logs)
            self.action_logs.append("========================================================")

        for p in self.players:
            p.game_bet = 0
            if p.chips <= 0 and not p.is_busted:
                p.chips = 0
                p.is_busted = True
                self.action_logs.append(f"📢 【アナウンス】{p.name} が完全に破産（トビ）しました。")

        self.show_intermission = True

    def get_state(self, p_id):
        return {
            "round_name": self.round_name,
            "board": [[c.suit, c.rank] for c in self.board],
            "highest_bet": self.highest_bet,
            "min_raise_increment": self.min_raise_increment,
            "current_turn_player_id": self.current_turn_player_id,
            "game_started": self.game_started,
            "show_intermission": self.show_intermission,
            "action_logs": self.action_logs,
            "chat_logs": self.chat_logs,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "chips": p.chips,
                    "status": p.status.name,
                    "is_busted": p.is_busted,
                    "round_bet": p.round_bet,
                    "game_bet": p.game_bet,
                    "hand": [[c.suit, c.rank] for c in p.hand] if (p.id == p_id or self.round_name == "結果発表") else None
                } for p in self.players
            ]
        }

class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.next_room_id = 1

    def assign_room(self, player_name, target_players=2):
        # 目標人数が一致しており、まだ満員になっていない待機中の部屋を探す
        for r_id, room in self.rooms.items():
            if room.target_players == target_players and len(room.players) < room.target_players and not room.game_started:
                p_id = room.add_player(player_name, is_human=True)
                return r_id, p_id
        # なければ新しい設定で部屋を作る
        r_id = self.next_room_id
        self.next_room_id += 1
        room = OnlinePokerRoom(r_id, target_players=target_players)
        self.rooms[r_id] = room
        p_id = room.add_player(player_name, is_human=True)
        return r_id, p_id

manager = RoomManager()
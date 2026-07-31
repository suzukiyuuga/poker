import random
from collections import Counter
import itertools
from enum import Enum, auto
from cpu_brain import decide_cpu_action
from hand_eval import evaluate_7_cards

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
    def __init__(self, suit, rank, display_rank=None):
        self.suit = suit
        self.rank = rank                    # 役判定用の元ランク ("2"～"A")
        self.value = RANK_VALUES[rank]      # 強さは今まで通り
        self.display_rank = display_rank if display_rank is not None else rank#display_rankは見た目用

    def __repr__(self):
        return f"[{self.suit}{self.display_rank}]"

class Deck:
    def __init__(self, display_base=0):
        self.display_base = display_base
        self.cards = []

        for s in SUITS:
            for i, r in enumerate(RANKS):
                display_rank = self.display_base + i
                self.cards.append(Card(s, r, display_rank))

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

    def reset_for_new_round(self):#プレイヤーが操作可能かどうか
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

class PotManager:#ショーダウンがある場合のお慢の処理全般
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
        
        self.target_players = target_players  # 指定の開始人数
        self.display_rank_base = 0  

    def add_player(self, name, is_human=True):
        if len(self.players) >= self.target_players or self.game_started: return None
        p_id = len(self.players)
        p = Player(p_id, name, is_human=is_human)
        self.players.append(p)
        self.action_logs.append(f"📢 {name} が参加しました。({len(self.players)}/{self.target_players})")
        
        # ★ ホストによる上書き後のチェック用にも使うためトリガー関数化
        self.check_start_trigger()
        return p_id

    def check_start_trigger(self):
        # プレイ人数が目標人数に達したら自動でゲームを開始する
        if not self.game_started and len(self.players) == self.target_players:
            self.start_new_game()

    def start_new_game(self):
        self.game_started = True
        self.show_intermission = False
        self.games_count += 1

        self.board.clear()
        self.display_rank_base = random.randint(0, 86)
        self.deck = Deck(display_base=self.display_rank_base)

        self.action_logs.append(
            f"🚨 ==================== 【 第 {self.games_count} 回 戦 開 始 】 ==================== 🚨"
        )

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

        for p in self.players:
            p.reset_for_new_round()

        if r_name == "プリフロップ":
            for p in self.players:
                p.round_bet = p.game_bet
        else:
            for p in self.players:
                p.round_bet = 0

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
        self.current_turn_player_id = None
        self.next_turn()

    def next_turn(self):
        alive_players = [
            p for p in self.players
            if p.status != HandStatus.FOLDED and not p.is_busted
        ]
        playable_players = [
            p for p in self.players
            if p.status == HandStatus.PLAYING and not p.is_busted
        ]

        if len(alive_players) <= 1:
            self.end_game()
            return

        if len(playable_players) == 0:
            self.advance_phase()
            return

        all_settled = all(
            p.acted and p.round_bet == self.highest_bet
            for p in playable_players
        )
        if all_settled:
            self.advance_phase()
            return

        checked = 0
        while checked < len(self.players):
            p = self.players[self.list_cursor]
            if p.status == HandStatus.PLAYING and not p.is_busted:
                self.current_turn_player_id = p.id
                return
            self.list_cursor = (self.list_cursor + 1) % len(self.players)
            checked += 1

        self.advance_phase()

    def think_cpu_action(self, cpu_player):
        act, amnt = decide_cpu_action(self, cpu_player)
        self.handle_action(cpu_player.id, act, amnt)

    def handle_action(self, p_id, act_type, amount):
        if self.current_turn_player_id != p_id: return False
        p = self.players[p_id]
        
        if act_type == "call":
            to_call = min(self.highest_bet - p.round_bet, p.chips)
            amount = to_call
            p.chips -= amount
            p.round_bet += amount
            p.game_bet += amount
            if p.chips == 0: p.status = HandStatus.ALL_IN
            self.action_logs.append(f"{p.name}: {'チェック' if amount == 0 else f'{amount}ptでコール'}{'（All-in!）' if p.chips == 0 else ''}")
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

        self.current_turn_player_id = None
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
        
        # ログ区切り線
        self.action_logs.append(f"🏁 ―――――――――― 【 第 {self.games_count} 回 戦 結 果 】 ―――――――――― 🏁")

        # ★ 全プレイヤーの手札と役判定をログに出力（フォールドした人も含める）
        self.action_logs.append("🃏 【参加者全員の手札と役】")
        for p in self.players:
            if not p.is_busted and p.hand:
                # 役の判定（7枚のカードから計算）
                score, name = evaluate_7_cards(p.hand + self.board)
                p.score = score
                p.hand_name = name
                
                # 伏せカード表記の整形
                c1, c2 = p.hand[0], p.hand[1]
                
                if p.status == HandStatus.FOLDED:
                    self.action_logs.append(f"  ・ {p.name:<8}: {c1} {c2} -> 【🏳️ FOLDED ({name})】")
                else:
                    self.action_logs.append(f"  ・ {p.name:<8}: {c1} {c2} -> 【{name}】")
            elif p.is_busted:
                self.action_logs.append(f"  ・ {p.name:<8}: ☠️ BUSTED")

        # 勝敗結果・ポット分配のログ出力
        if len(survivors) == 1:
            winner = survivors[0]
            total_pot = sum(p.game_bet for p in self.players)
            winner.chips += total_pot
            self.action_logs.append(f"🏆 勝者: {winner.name} (他プレイヤー全員フォールド)")
            self.action_logs.append(f"💰 獲得チップ: {total_pot} pt")
        else:
            dist_logs = self.pot_manager.distribute_pots(self.players)
            self.action_logs.extend(dist_logs)

        # 全プレイヤーの現在の最終残高をログに出力
        self.action_logs.append("📊 【各プレイヤーの最終所持チップ】")
        for p in self.players:
            status_str = " (BUSTED)" if p.chips <= 0 else ""
            self.action_logs.append(f"  ・ {p.name}: {p.chips} pt{status_str}")

        # 破産（トビ）チェック
        for p in self.players:
            p.game_bet = 0
            if p.chips <= 0 and not p.is_busted:
                p.chips = 0
                p.is_busted = True
                self.action_logs.append(f"📢 【アナウンス】{p.name} が完全に破産（トビ）しました。")

        self.action_logs.append("🏁 ―――――――――――――――――――――――――――――――――――――――――――――― 🏁")
        self.show_intermission = True

    def get_state(self, p_id):
        return {
            "round_name": self.round_name,
            "board": [[c.suit, c.display_rank] for c in self.board],
            "highest_bet": self.highest_bet,
            "min_raise_increment": self.min_raise_increment,
            "current_turn_player_id": self.current_turn_player_id,
            "game_started": self.game_started,
            "show_intermission": self.show_intermission,
            "action_logs": self.action_logs,
            "chat_logs": self.chat_logs,
            "target_players": self.target_players,  # クライアント同期用に追加
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "chips": p.chips,
                    "status": p.status.name,
                    "is_busted": p.is_busted,
                    "round_bet": p.round_bet,
                    "game_bet": p.game_bet,
                    "hand": [[c.suit, c.display_rank] for c in p.hand]
                            if (p.id == p_id or self.round_name == "結果発表") else None
                } for p in self.players
            ]
        }

class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.next_room_id = 1

    def assign_room(self, player_name):
        # 1. 人数は関係なく、まだゲームが始まっていない空いている待機部屋があれば合流させる
        for r_id, room in self.rooms.items():
            if not room.game_started and len(room.players) < room.target_players:
                p_id = room.add_player(player_name, is_human=True)
                return r_id, p_id, False  # ホストフラグはFalse
        
        # 2. 合流できる部屋がなければ、ひとまず初期値2人で新規部屋（自分がホスト）を作成する
        r_id = self.next_room_id
        self.next_room_id += 1
        room = OnlinePokerRoom(r_id, target_players=2)
        self.rooms[r_id] = room
        p_id = room.add_player(player_name, is_human=True)
        return r_id, p_id, True  # ホストフラグはTrue

    def leave_room(self, room_id, player_id):
        room = self.rooms.get(room_id)
        if not room:
            return False
            
        room.players = [p for p in room.players if p.id != player_id]
        room.action_logs.append(f"🏃 プレイヤー(ID:{player_id}) が退室しました。")
        
        if not room.game_started and len(room.players) == 0:
            del self.rooms[room_id]
            
        return True

manager = RoomManager()
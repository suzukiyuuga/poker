card={"suit": "♥", "rank": "A"}
print(card["suit"])
RANK_VALUES = {r: i + 2 for i, r in enumerate(card)}
print(RANK_VALUES)
from simulator.rules import STANDARD_6D_H17, STANDARD_6D_S17
from simulator.strategy_table import build_soft_table, DEALER_LABELS

def show_soft(rules, label):
    tbl = build_soft_table(rules)
    print(f"  Soft totals -- {label}")
    header = "       " + "".join(f"{l:>5}" for l in DEALER_LABELS)
    print(f"  {header}")
    print("  " + "-"*57)
    for total in range(13, 21):
        row = tbl[total]
        hand_label = f"A,{total-11}"
        cells = "".join(f"{c:>5}" for c in row)
        print(f"  {hand_label:>5} {cells}")
    print()

show_soft(STANDARD_6D_H17, "6D H17 (current)")
show_soft(STANDARD_6D_S17, "6D S17 (current)")

print("  What the table SHOULD show (per BJA / correct strategy):")
print("  Soft 13 (A,2): H  H  H  D  D  H  H  H  H  H")
print("  Soft 14 (A,3): H  H  H  D  D  H  H  H  H  H")
print("  Soft 15 (A,4): H  H  D  D  D  H  H  H  H  H")
print("  Soft 16 (A,5): H  H  D  D  D  H  H  H  H  H")
print("  Soft 17 (A,6): H  D  D  D  D  H  H  H  H  H")
print("  Soft 18 (A,7): D  D  D  D  D  S  S  H  H  H  <- user says vs 2 should be D")
print("  Soft 19 (A,8): S  S  S  S  S  S  S  S  S  S  (H17) / D vs 6 (S17)")
print("  Soft 20 (A,9): S  S  S  S  S  S  S  S  S  S")

#!/usr/bin/env python3
"""金字塔纸牌 (Pyramid Solitaire) —— 终端版。

规则: 28 张牌摆成 7 层金字塔, 只有"完全暴露"(下方两张牌都已移走)的牌
和废牌堆顶可用。移走点数之和为 13 的牌对(A=1..K=13), K 可单独移走。
清掉整个金字塔即获胜。
"""

import argparse
import random
import secrets
import sys

RANK_NAME = {1: "A", 11: "J", 12: "Q", 13: "K"}
SUITS = ["♠", "♥", "♦", "♣"]


def card_name(card):
    r, s = card
    return f"{RANK_NAME.get(r, r)}{SUITS[s]}"


def new_deck(rng):
    deck = [(r, s) for r in range(1, 14) for s in range(4)]
    rng.shuffle(deck)
    return deck


class Game:
    """一局金字塔纸牌。"""

    ROWS = 7

    def __init__(self, seed=None):
        rng = random.Random(seed) if seed is not None else random.Random(secrets.randbits(64))
        deck = new_deck(rng)
        self.pyr = []
        i = 0
        for r in range(self.ROWS):
            row = []
            for _ in range(r + 1):
                row.append(deck[i])
                i += 1
            self.pyr.append(row)
        self.stock = deck[i:]  # 24 张
        self.waste = []
        self.moves = 0

    # ---- 状态查询 ----
    def exposed(self):
        """返回完全暴露的金字塔牌: [(r, c, card), ...]。"""
        out = []
        for r in range(self.ROWS):
            for c in range(r + 1):
                card = self.pyr[r][c]
                if card is None:
                    continue
                if r == self.ROWS - 1:
                    out.append((r, c, card))
                elif self.pyr[r + 1][c] is None and self.pyr[r + 1][c + 1] is None:
                    out.append((r, c, card))
        return out

    def waste_top(self):
        return self.waste[-1] if self.waste else None

    def pyramid_cleared(self):
        return all(card is None for row in self.pyr for card in row)

    # ---- 操作 ----
    def draw(self):
        """从牌堆翻一张到废牌堆。无牌可翻返回 False。"""
        if not self.stock:
            return False
        self.waste.append(self.stock.pop())
        return True

    def remove(self, picks):
        """picks: [('p', r, c), ...] 或 [('w',), ...]。成功返回 True。

        合法性: 1 张必须为 K; 2 张点数和必须为 13; 金字塔牌必须已暴露;
        不能选同一张牌两次。
        """
        if len(picks) not in (1, 2) or len(set(picks)) != len(picks):
            return False
        cards = []
        exposed = {(r, c) for r, c, _ in self.exposed()}
        for p in picks:
            if p[0] == "p":
                _, r, c = p
                if (r, c) not in exposed:
                    return False
                cards.append(self.pyr[r][c])
            elif p[0] == "w":
                top = self.waste_top()
                if top is None:
                    return False
                cards.append(top)
            else:
                return False
        if len(cards) == 1:
            if cards[0][0] != 13:
                return False
        else:
            if cards[0][0] + cards[1][0] != 13:
                return False
        for p in picks:
            if p[0] == "p":
                self.pyr[p[1]][p[2]] = None
            else:
                self.waste.pop()
        self.moves += 1
        return True

    def find_move(self):
        """找一个合法走法(贪心: 优先金字塔牌), 找不到返回 None。"""
        pool = [("p", r, c, card) for r, c, card in self.exposed()]
        top = self.waste_top()
        if top is not None:
            pool.append(("w", None, None, top))
        for kind, r, c, card in pool:
            if card[0] == 13:
                return [(kind,) if kind == "w" else (kind, r, c)]
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                if pool[i][3][0] + pool[j][3][0] == 13:
                    a = ("w",) if pool[i][0] == "w" else ("p", pool[i][1], pool[i][2])
                    b = ("w",) if pool[j][0] == "w" else ("p", pool[j][1], pool[j][2])
                    return [a, b]
        return None

    # ---- 展示 ----
    def render(self):
        lines = []
        exposed_ids = {}
        for n, (r, c, card) in enumerate(self.exposed(), 1):
            exposed_ids[(r, c)] = n
        for r in range(self.ROWS):
            parts = []
            for c in range(r + 1):
                card = self.pyr[r][c]
                if card is None:
                    parts.append("    ")
                elif (r, c) in exposed_ids:
                    parts.append(f"[{exposed_ids[(r, c)]:>2}]")
                else:
                    parts.append(f" {card_name(card):>3}")
            indent = " " * (3 * (self.ROWS - 1 - r))
            lines.append(indent + " ".join(parts))
        lines.append("")
        names = ", ".join(f"{n}:{card_name(card)}" for n, (_, _, card) in
                          enumerate(self.exposed(), 1))
        lines.append(f"可移: {names}" if names else "可移: (无)")
        top = self.waste_top()
        lines.append(f"废牌堆顶 [w]: {card_name(top) if top else '(无)'}   "
                     f"牌堆: {len(self.stock)} 张   步数: {self.moves}")
        return "\n".join(lines)


def auto_play(seed=None, verbose=False):
    """贪心机器人: 能移就移, 否则翻牌。返回 (win, moves)。必终止。"""
    g = Game(seed)
    while True:
        if g.pyramid_cleared():
            return True, g.moves
        mv = g.find_move()
        if mv:
            g.remove(mv)
        elif g.draw():
            pass
        else:
            return False, g.moves


def play_interactive(seed=None):
    g = Game(seed)
    print("=== 金字塔纸牌 ===")
    print("命令: <编号> [<编号>] 移牌(K 可单独移) | w=废牌堆顶参与配对")
    print("      d=翻牌 | h=帮助 | q=退出\n")
    while True:
        print(g.render())
        if g.pyramid_cleared():
            print(f"\n🎉 胜利! 金字塔清空, 共用 {g.moves} 步。")
            return 0
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return 0
        if raw in ("q", "quit", "exit"):
            print("已退出。")
            return 0
        if raw in ("h", "help"):
            print("把点数加起来等于 13 的两张牌移走(A=1,Q=12,J=11,K=13 单独移)。")
            print("只有标了 [编号] 的牌和废牌堆顶 [w] 可以移。例: `1 3` / `2` / `w 1` / `d`")
            continue
        if raw in ("d", "draw"):
            if not g.draw():
                print("牌堆已空, 翻不了牌。")
            continue
        exposed = g.exposed()
        idmap = {str(n): ("p", r, c) for n, (r, c, _) in enumerate(exposed, 1)}
        idmap["w"] = ("w",)
        toks = raw.split()
        if not all(t in idmap for t in toks) or len(toks) not in (1, 2):
            print("命令无效。试试 `h` 看帮助。")
            continue
        picks = [idmap[t] for t in toks]
        if g.remove(picks):
            print("移走 ✓")
        else:
            print("不能这样移(需要: 单张K, 或两张点数和=13)。")
        if not g.find_move() and not g.stock and not g.pyramid_cleared():
            print(g.render())
            print("\n😞 无牌可走, 牌堆也空了——失败。")
            return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="金字塔纸牌 (Pyramid Solitaire)")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--auto", action="store_true", help="贪心机器人自动玩一局")
    args = ap.parse_args(argv)
    if args.auto:
        win, moves = auto_play(args.seed)
        print(f"{'胜利' if win else '失败'}: {moves} 步" +
              (f" (seed={args.seed})" if args.seed is not None else ""))
        return 0 if win else 1
    if not sys.stdin.isatty():
        print("error: 交互模式需要终端, 管道请用 --auto", file=sys.stderr)
        return 2
    return play_interactive(args.seed)


if __name__ == "__main__":
    raise SystemExit(main())

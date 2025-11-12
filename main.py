"""
АДПАЦФ — построение дерева целей и функций (до 4 уровней).
АДП ОСЭ — оценка факторов по формуле H = -q * ln(1 - p').

=== АДПАЦФ: Построение дерева целей и функций ===
1. Пользователь вводит главную цель.
2. Предлагаем добавить подцели (до 4 уровней).
3. Циклично уточняем добавить ли еще и проверяем глубину дерева.
4. Вывод: итоговая структура в виде дерева.
=== АДП ОСЭ: Оценка факторов ===
5. Пользователь вводит названия факторов
6. Пользователь вводит p' и q (вероятность достижения цели и вероятность использования фактора) для каждой из целей
7. Вывод H для каждого фактора
"""

import math
from typing import List, Optional

class GoalNode:
    def __init__(self, name: str, level: int = 1, parent: Optional['GoalNode'] = None):
        self.name = name
        self.level = level
        self.parent = parent
        self.children: List['GoalNode'] = []

    def add_child(self, child_name: str):
        if self.level >= 4:
            print(f"Нельзя добавить уровень глубже 4 (текущий уровень: {self.level})")
            return None
        child = GoalNode(child_name, self.level + 1, self)
        self.children.append(child)
        return child

    def print_tree(self, indent: str = ""):
        print(f"{indent}- {self.name} (уровень {self.level})")
        for ch in self.children:
            ch.print_tree(indent + "  ")


def build_goal_tree() -> GoalNode:
    print("=== АДПАЦФ: Построение дерева целей и функций ===")
    root_name = input("Введите главную цель: ").strip()
    root = GoalNode(root_name, level=1)

    def add_subgoals(node: GoalNode):
        while True:
            ans = input(f"Добавить подцель для '{node.name}'? (y/n): ").strip().lower()
            if ans != 'y':
                break
            sub_name = input(f"Введите название подцели для '{node.name}': ").strip()
            child = node.add_child(sub_name)
            if child:
                add_subgoals(child)

    add_subgoals(root)

    print("\n=== Итоговая структура целей ===")
    root.print_tree()
    return root


def collect_goals(node: GoalNode) -> List[GoalNode]:
    result = [node]
    for child in node.children:
        result.extend(collect_goals(child))
    return result


def adp_ose(goals: List[GoalNode]):
    print("\n=== АДП ОСЭ: Оценка факторов ===")
    factors = []
    while True:
        name = input("Введите название фактора (или Enter для завершения): ").strip()
        if not name:
            break
        factors.append(name)

    results = []
    for goal in goals:
        for factor in factors:
            print(f"\nОценка влияния фактора '{factor}' на цель '{goal.name}':")
            try:
                p_prime = float(input("  Введите p' (вероятность достижения цели, 0..1): "))
                q = float(input("  Введите q (вероятность использования фактора, 0..1): "))
                if not (0 <= p_prime <= 1 and 0 <= q <= 1):
                    raise ValueError
            except ValueError:
                print(" Некорректные значения, пропуск...")
                continue

            if p_prime <= 0 or q <= 0:
                H = 0.0
            elif p_prime >= 1:
                H = q * 20.0  # условное ограничение, чтобы не уходить в бесконечность
            else:
                H = -q * math.log(1 - p_prime)

            results.append((goal.name, factor, round(H, 4)))
            print(f"  → H = -{q} * ln(1 - {p_prime}) = {round(H,4)}")

    print("\n=== Итоговые оценки H ===")
    for goal_name, factor_name, H in results:
        print(f"Цель: {goal_name:<30} | Фактор: {factor_name:<20} | H = {H}")


def main():
    root = build_goal_tree()
    all_goals = collect_goals(root)
    adp_ose(all_goals)


if __name__ == "__main__":
    main()
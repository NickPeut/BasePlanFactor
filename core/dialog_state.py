from models.goal import GoalNode


class DialogState:
    def __init__(self):
        # какая подсистема сейчас: adpacf | adpose
        self.phase: str = "adpacf"
        # внутреннее состояние внутри фазы или режима редактирования
        self.state: str = "ask_root"

        # дерево целей
        self.root: GoalNode | None = None
        self.current_node: GoalNode | None = None
        self.max_level: int = 3

        # ОСЭ
        self.goals_ordered: list[GoalNode] = []
        self.current_goal_idx: int = 0
        self.current_factor_name: str | None = None
        self.factors_results: list[dict] = []
        self._p: float | None = None  # используется в обычном ОСЭ-диалоге

        # словари имён
        self.used_names: set[str] = set()          # все имена (цели + факторы), в нижнем регистре
        self.goal_by_name: dict[str, GoalNode] = {}  # имя (lower) -> узел цели
        self.factor_set: set[str] = set()          # имена факторов (lower)

        # редактирование
        self.prev_state: str | None = None         # предыдущее состояние до входа в режим редактирования
        self.edit_goal_target: GoalNode | None = None

        # мастер добавления цели с факторами
        self.add_goal_name: str | None = None
        self.add_goal_current_goal: GoalNode | None = None
        self.add_goal_factors_list: list[str] = []
        self.add_goal_factor_index: int = 0
        self.add_goal_current_factor: str | None = None
        self.add_goal_tmp_p: float | None = None


dialog = DialogState()

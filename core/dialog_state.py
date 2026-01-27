from db.goal import GoalNode


class DialogState:
    def __init__(self):
        self.phase: str = "adpacf"
        self.state: str = "ask_root"
        self.active_scheme_id = None

        self.root: GoalNode | None = None
        self.current_node: GoalNode | None = None
        self.max_level: int = 3

        self.goals_ordered: list[GoalNode] = []
        self.current_goal_idx: int = 0
        self.current_factor_name: str | None = None
        self.factors_results: list[dict] = []
        self._p: float | None = None

        self.used_names: set[str] = set()
        self.goal_by_name: dict[str, GoalNode] = {}
        self.factor_set: set[str] = set()

        self.prev_state: str | None = None
        self.edit_goal_target: GoalNode | None = None

        self.add_goal_name: str | None = None
        self.add_goal_current_goal: GoalNode | None = None
        self.add_goal_factors_list: list[str] = []
        self.add_goal_factor_index: int = 0
        self.add_goal_current_factor: str | None = None
        self.add_goal_tmp_p: float | None = None

        self.clf_state: str | None = None
        self.clf_level: int = 1
        self.clf_parent_goal: GoalNode | None = None
        self.clf_c1_id: int | None = None
        self.clf_c2_id: int | None = None
        self.clf_pairs: list[tuple[str, str]] = []
        self.clf_pair_idx: int = 0


dialog = DialogState()

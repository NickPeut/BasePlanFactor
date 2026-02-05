from db.goal import GoalNode


class DialogState:
    def __init__(self):
        self.phase = "adpacf"
        self.state = "ask_root"
        self.active_scheme_id = None

        self.root = None
        self.current_node = None
        self.max_level = 3

        self.used_names = set()
        self.goal_by_name = {}

        self.factor_name = None
        self._ose_goal = None
        self._p = None
        self.factors_results = []
        self.factor_set = set()

        self.clfs = []
        self.clf_tmp_name = None
        self.clf_indices = None
        self.clf_level = 1
        self.clf_parent_goal = None
        self.clf_done = False

        self.prev_state = None
        self.edit_goal_target = None

        self.add_goal_name = None
        self.add_goal_current_goal = None
        self.add_goal_factors_list = []
        self.add_goal_factor_index = 0
        self.add_goal_current_factor = None
        self.add_goal_tmp_p = None

        self.clf_state: str | None = None
        self.clf_level: int = 1
        self.clf_parent_goal: GoalNode | None = None
        self.clf_c1_id: int | None = None
        self.clf_c2_id: int | None = None
        self.clf_pairs: list[tuple[str, str]] = []
        self.clf_pair_idx: int = 0


dialog = DialogState()

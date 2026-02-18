from db.goal import GoalNode


class DialogState:
    def __init__(self):
        self.phase = "adpacf"
        self.state = "ask_root"
        self.active_scheme_id = None

        self.root = None
        self.current_node = None
        self.max_level = 15
        self.max_cls = 4

        self.used_names = set()
        self.goal_by_name = {}

        self.current_factor_name = None
        self._ose_goal = None
        self._p = None
        self._q = None
        self.factors_results = []
        self.ose_goals = []
        self.ose_goal_idx = 0
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


dialog = DialogState()

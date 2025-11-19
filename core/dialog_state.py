from models.goal import GoalNode


class DialogState:
    def __init__(self):
        self.phase = "adpacf"
        self.state = "ask_root"

        # дерево целей
        self.root: GoalNode | None = None
        self.current_node: GoalNode | None = None
        self.max_level = 3

        # ОСЭ
        self.goals_ordered = []
        self.current_goal_idx = 0
        self.current_factor_name = None
        self.factors_results = []
        self._p = None

        # хранилища для команд редактирования
        self.used_names = set()
        self.goal_by_name = {}    # name -> GoalNode
        self.factor_set = set()   # имена факторов


dialog = DialogState()

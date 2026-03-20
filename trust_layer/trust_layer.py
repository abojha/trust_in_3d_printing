# trust_layer/trust_layer.py

import math


class TrustLayer:
    """
    Exact implementation of the reference trust model.
    """

    def __init__(
        self,
        *,
        theta=0.6,
        alpha=3.0,
        omega=0.4,
        T_init=0.75,
        T_min=0.50,
    ):
        # Parameters
        self.theta = theta
        self.alpha = alpha
        self.omega = omega
        self.T_min = T_min

        # States
        self.S_cmd = 0.0
        self.S_exec = 0.0
        self.T = T_init

    def update_from_deviation(self, acc_cmd, acc_exec):
        """
        One-step trust update with immediate PAUSE logic.
        PAUSE fires instantly when T < T_min.
        """
        # 1. Accumulate abnormality
        self.S_cmd = self.theta * self.S_cmd + acc_cmd
        self.S_exec = self.theta * self.S_exec + acc_exec

        # 2. Abnormality mapping
        c_cmd = 1 - math.exp(-self.alpha * self.S_cmd)
        c_exec = 1 - math.exp(-self.alpha * self.S_exec)

        # 3. Consistency scores
        CCT = 1 - c_cmd
        EFCT = 1 - c_exec

        # 4. Evidence aggregation (min-based, safety-first)
        E = min(CCT, EFCT)

        # 5. Trust update
        self.T = self.omega * self.T + (1 - self.omega) * E

        # 6. Immediate PAUSE decision
        decision = "PAUSE" if self.T < self.T_min else "ALLOW"

        return {
            "trust": self.T,
            "decision": decision,
            "S_cmd": self.S_cmd,
            "S_exec": self.S_exec,
            "E": E
        }

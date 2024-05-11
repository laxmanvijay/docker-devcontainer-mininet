from base_topo import Graph

class BCubeTopo(Graph):
    def __init__(self) -> None:
        super().__init__("b-cube")

        self.pods = 4

        self.hosts = []

        self.core_switches = []
        self.agg_switches = []

    def generate(self, pod_count: int) -> None:
        self.hosts = []
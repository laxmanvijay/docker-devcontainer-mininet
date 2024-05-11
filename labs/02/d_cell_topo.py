from base_topo import Graph

class DCellTopo(Graph):
    def __init__(self) -> None:
        super().__init__("d-cell")

        self.pods = 4

        self.hosts = []

        self.core_switches = []
        self.agg_switches = []

    def generate(self, pod_count: int) -> None:
        self.hosts = []
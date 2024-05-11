from .composable_base import Composable
import networkx as nx
import matplotlib.pyplot as plt
import random

class NetworkxVisualizationComposer(Composable):
    def __init__(self) -> None:
        self.graph = nx.Graph()

    def add_node(self, name: str) -> None:
        self.graph.add_node(name)

    def add_edge(self, n1: str, n2: str) -> None:
        self.graph.add_edge(n1, n2)

    def remove_edge(self, n1: str, n2: str):
        pass
        # self.graph.remove_edge(n1, n2)
    
    def draw(self) -> None:
        pos = nx.nx_agraph.graphviz_layout(self.graph, prog="neato")
        nx.draw(self.graph, pos, with_labels = True)
        plt.show()
    
    def compute_dijkstra(self, src: str, dst: str) -> int:
        return nx.single_source_dijkstra(self.graph, src, dst)

class SimpleTree(NetworkxVisualizationComposer):
    def __init__(self) -> None:
        super().__init__()
        self.generate()

    def generate(self):
        nodes = list(range(0,100))

        for i in nodes:
            self.add_node(i)
        
        r1 = nodes.copy()
        random.shuffle(r1)

        r2 = nodes.copy()
        random.shuffle(r2)

        for i in zip(r1, r2):
            self.add_edge(i[0], i[1])
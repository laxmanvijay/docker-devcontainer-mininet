from collections import defaultdict
import heapq
from operator import itemgetter
import random
import sys
from composables.composable_base import Composable
from exceptions import DuplicateNodeNameException, NodeTypeNotFoundException
from joblib import Parallel, delayed

import multiprocessing
from multiprocessing import Manager

class Edge:
    def __init__(self):
        self.lnode = None
        self.rnode = None
    
    def remove(self):
        self.lnode.edges.remove(self)
        self.rnode.edges.remove(self)
        self.lnode = None
        self.rnode = None

# Class for a node in the graph
class Node:
    def __init__(self, id, type):
        self.edges = []
        self.id = id
        self.type = type

    # Add an edge connected to another node
    def add_edge(self, node):
        edge = Edge()
        edge.lnode = self
        edge.rnode = node
        self.edges.append(edge)
        return edge

    def __le__(self, other):
        return self

    def __lt__(self, other):
        return self

    # Remove an edge from the node
    def remove_edge(self, edge):
        self.edges.remove(edge)

    # Decide if another node is a neighbor
    def is_neighbor(self, node):
        for edge in self.edges:
            if edge.lnode == node or edge.rnode == node:
                return True
        return False

class Graph:
    def __init__(self, name: str) -> None:
        self.composables: list[Composable]  = []
        self.graph_name = name
        
        self.nodes: list[Node] = []
        self.node_names: list[str] = []
        self.edges: list[Edge] = []

        self.adjacency_matrix = None
    
    def add_composable(self, composable: Composable):
        self.composables.append(composable)
    
    def add_node(self, n: str, t: str) -> Node:
        if n in self.node_names:
            raise DuplicateNodeNameException()
        
        nd = Node(n, t)
        self.nodes.append(nd)
        self.node_names.append(n)

        for c in self.composables:
            c.add_node(n)
            
        return nd
    
    def add_edge(self, n1: str, n2: str):
        n_1 = self.nodes[self.node_names.index(n1)]
        n_2 = self.nodes[self.node_names.index(n2)]

        n_1.add_edge(n_2)
        n_2.add_edge(n_1)

        for c in self.composables:
            c.add_edge(n1, n2)

    def get_node_by_id(self, id: str) -> Node:
        for n in self.nodes:
            if n.id == id:
                return n
        
        return None
            
    def remove_edge(self, n: str, t: str):
        edge_to_remove = None
        n_1 = self.nodes[self.node_names.index(n)]

        for e in n_1.edges:
            if e.rnode.id == t and e.lnode.id == n:
                edge_to_remove = e
                break

        n_1.remove_edge(edge_to_remove)

        for c in self.composables:
            c.remove_edge(n, t)

    def create_nodes_from_array(self, node_defn_array: list) -> None:
        for n in node_defn_array:
            if n[1].get('type') == None:
                raise NodeTypeNotFoundException()
            self.add_node(n[0], n[1].get('type'))
            
    def generate_adjancency_matrix(self):
        if self.adjacency_matrix != None:
            return self.adjacency_matrix
        
        adj = [[float('inf') for i in range(len(self.nodes))] for j in range(len(self.nodes))]

        for i in range(len(self.nodes)):
            for j in range(len(self.nodes)):
                if self.nodes[i].is_neighbor(self.nodes[j]):
                    adj[i][j] = 1

        self.adjacency_matrix = adj

        return adj

    def define_topology(self):
        pass

    def compute_dijikstra_using_spt(self, src: Node, dst: Node):
        src_idx = self.node_names.index(src.id)
        dst_idx = self.node_names.index(dst.id)

        adj_mat = self.generate_adjancency_matrix()

        dist = [sys.maxsize] * len(self.nodes)
        dist[src_idx] = 0
        sptSet = [False] * len(self.nodes)
 
        for _ in range(len(self.nodes)):

            min_idx = None
            min_val = sys.maxsize
            for u in range(len(self.nodes)):
                if dist[u] < min_val and sptSet[u] == False:
                    min_val = dist[u]
                    min_idx = u
            
            if min_idx != None:
                sptSet[min_idx] = True
                
            for y in range(len(self.nodes)):
                if adj_mat[min_idx][y] > 0 and sptSet[y] == False and dist[min_idx] != sys.maxsize and dist[y] > dist[min_idx] + adj_mat[min_idx][y]:
                        dist[y] = dist[min_idx] + adj_mat[min_idx][y]

        return dist[dst_idx]
    
    def compute_dijkstra_using_heap(self, src: Node, dst: Node = None):
        visited = set()
        priority_queue = []

        pathMap = {}

        distance = defaultdict(lambda: sys.maxsize)
        distance[src.id] = 0

        heapq.heappush(priority_queue, (0, src))
    
        while priority_queue:

            _, node = heapq.heappop(priority_queue)
            visited.add(node)
    
            for edge in node.edges:
                if edge.rnode in visited:
                    continue
                    
                new_distance = distance[node.id] + 1

                if distance[edge.rnode.id] > new_distance:
                    distance[edge.rnode.id] = new_distance

                    pathMap[edge.rnode] = node

                    heapq.heappush(priority_queue, (new_distance, edge.rnode))
            
        return distance, pathMap
    
    def path(self, previous, node_start, node_end):
        route = []

        node_curr = node_end    
        while True:
            route.append(node_curr)
            if previous.get(node_curr).id == node_start.id:
                route.append(node_start)
                break
            
            node_curr = previous[node_curr]
        
        route.reverse()
        return route
    
    def compute_dijikstra_for_all_hosts(self):
        hosts = self.get_all_hosts()

        computed_paths = Manager().dict()

        def processInput(idx):
            t_res = []
            remaining_hosts = hosts[0:idx] + hosts[idx+1:len(hosts)]
            print(f"host {idx+1} of {len(hosts)}")
            for rem in remaining_hosts:
                path_name = None
                if computed_paths.get(f"{hosts[idx].id}:{rem.id}") != None:
                    path_name = f"{hosts[idx].id}:{rem.id}"
                elif computed_paths.get(f"{rem.id}:{hosts[idx].id}") != None:
                    path_name = f"{rem.id}:{hosts[idx].id}"
                
                if path_name != None:
                    t_res.append(computed_paths[path_name])
                
                else:
                    path_name = f"{hosts[idx].id}:{rem.id}"
                    computed_paths[path_name] = self.compute_dijkstra_using_heap(hosts[idx], rem)[0][rem.id]
                    t_res.append(computed_paths[path_name])
            
            return t_res
        
        num_cores = multiprocessing.cpu_count()
        print(f"parallelising using {num_cores} cores")

        results = Parallel(n_jobs=num_cores, prefer="threads")(delayed(processInput)(i) for i in range(0, len(hosts)))
        
        return [i for sublist in results for i in sublist]

    
    def get_all_hosts(self):
        host_idxs = list(filter(lambda x: x[1].startswith('h'), enumerate(self.node_names)))

        hosts = []

        for id in host_idxs:
            hosts.append(self.nodes[id[0]])
        
        return hosts

    def compute_yen_ksp(self, node_start: Node, node_end: Node, max_k=2):
        distances, previous = self.compute_dijkstra_using_heap(node_start)
        
        A = [{'cost': distances[node_end.id], 
            'path': self.path(previous, node_start, node_end)}]
        B = []
        
        if not A[0]['path']: return A
        
        for k in range(1, max_k):
            for i in range(0, len(A[-1]['path']) - 1):
                node_spur = A[-1]['path'][i]
                path_root = A[-1]['path'][:i+1]
                
                edges_removed = []
                for path_k in A:
                    curr_path = path_k['path']
                    if len(curr_path) > i and path_root == curr_path[:i+1]:
                        self.remove_edge(curr_path[i].id, curr_path[i+1].id)
                        
                        edges_removed.append([curr_path[i], curr_path[i+1]])
                
                path_spur, prev_path_spur = self.compute_dijkstra_using_heap(node_spur, node_end)
                
                path_total = path_root[:-1] + self.path(prev_path_spur, node_spur, node_end)
                dist_total = distances[node_spur.id] + path_spur[node_end.id]
                potential_k = {'cost': dist_total, 'path': path_total}
                
                if not (potential_k in B):
                    B.append(potential_k)
                
                for edge in edges_removed:
                    self.add_edge(edge[0].id, edge[1].id)
            
            if len(B):
                B = sorted(B, key=itemgetter('cost'))
                A.append(B[0])
                B.pop(0)
            else:
                break
        
        return A
    
    def compute_yen_for_server_permutation_pairs(self):
        original_hosts = self.get_all_hosts()

        shuffled_hosts = self.get_all_hosts()
        random.shuffle(shuffled_hosts)

        permuted_pairs = zip(original_hosts, shuffled_hosts)

        computed_paths = {}
        eight_ecmp = {}
        sixty_four_ecmp = {}

        for h in permuted_pairs:
            path_name = None
            if computed_paths.get(f"{h[0].id}:{h[1].id}") != None:
                path_name = f"{h[0].id}:{h[1].id}"
            elif computed_paths.get(f"{h[1].id}:{h[0].id}") != None:
                path_name = f"{h[1].id}:{h[0].id}"
            
            if computed_paths.get(path_name) == None:
                path_name = f"{h[0].id}:{h[1].id}"
                computed_paths[path_name] = self.compute_yen_ksp(h[0], h[1], 64)
            
            eight_ecmp[path_name] = self.get_ecmp_paths(h, computed_paths, 8)
            sixty_four_ecmp[path_name] = self.get_ecmp_paths(h, computed_paths, 64)
        
        return computed_paths, eight_ecmp, sixty_four_ecmp


    def get_ecmp_paths(self, host_pair: tuple[Node, Node], computed_paths: dict[str, list], required_path_count: int):
        path_name = f"{host_pair[0].id}:{host_pair[1].id}"

        paths_equal_to_shortest_path = []

        try:
            all_paths = computed_paths[path_name]

            shortest_path = all_paths[0]

            for p in all_paths[1:]:
                if len(p['path']) == len(shortest_path['path']):
                    paths_equal_to_shortest_path.append(p)
                
                if len(paths_equal_to_shortest_path) == required_path_count:
                    break

            return paths_equal_to_shortest_path
        
        except KeyError:
            print("Key not found for hosts: {host_pair[0].id} and {host_pair[1].id}")
            return []
    
    def calculate_centrality(self, computed_paths: dict[str, list]):
        centrality_of_switches = {}

        for _, cp in computed_paths.items():
            for path in cp:
                for node in path['path']:
                    if node.id.startswith('s'):
                        centrality_of_switches[node.id] = (centrality_of_switches.get(node.id) or 0) + 1
        
        return centrality_of_switches
    

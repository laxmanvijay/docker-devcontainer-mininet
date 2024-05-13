from base_topo import Graph

class DCellTopo(Graph):
    def __init__(self, n, l) -> None:
        super().__init__("d-cell")

        self.l = l # level in dcell starts from 0 ( total number of levels )
        self.n = n # denoted as n in the paper ( number of servers in each cell )

        self.hosts = []
        
        self.create_nodes_from_array(self.hosts)
        
        self.switches = []

        self.switch_count = 0
        self.host_count = 0

        self.virtual_edge_count = 0

    def generate_dcell_structure(self, level: int) -> None:
        if level == 0:
            switch = self.add_node(f's_{level}_{self.switch_count}')
            self.switch_count += 1

            temp_host_arr = []

            self.switches.append(switch)

            for i in range (self.n):
                h = f'h_{self.host_count}'
                self.host_count += 1

                self.add_node(h, 'host')
                self.host_count += 1

                temp_host_arr.append({
                    'host': h,
                    'connected': False
                })

                self.hosts.append(h)

                self.add_edge(switch.id, h)
            
            return temp_host_arr

        else:
            hosts_arr = []

            num_server_in_prev_level = self.get_num_server(level - 1)
            num_of_cells_in_curr_level = num_server_in_prev_level + 1

            for c in range(num_of_cells_in_curr_level):
                hosts_arr.append({c: self.generate_dcell_structure(self, level-1)})

            for i in range(num_of_cells_in_curr_level - 1):
                for j in range(i+1, num_of_cells_in_curr_level):
                    self.connect_virtual_hosts(hosts_arr[i], hosts_arr[j])

            out = []
            for sublist in hosts_arr:
                out.extend(sublist)
            
            for i in out:
                i['connected'] = False

            return out


    def connect_virtual_hosts(self, v1: list[dict[str, any]], v2: list[dict[str, any]]):
        n1 = list(filter(lambda x: x['connected'] == False, v1))[0]
        n2 = list(filter(lambda x: x['connected'] == False, v2))[0]

        n1['connected'] = True
        n2['connected'] = True

        self.virtual_edge_count += 1

        self.add_edge(n1['host'], n2['host'])
                    

    def get_num_server(self, level: int):
        if level == 0:
            return self.n
        
        serv_in_prev = self.get_num_server(level - 1)

        return serv_in_prev * (serv_in_prev + 1)

        

            
        




from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, arp
import ipaddress

# h1 ping ser
# First h1 checks if ser's ip is in the same subnet
# Since it is in a different subnet, it is sent to the gateway ip
# But since h1 doesn't know the mac address of the gateway, it sends an arp request
# Once the gateway receives an arp, it sends back its mac address
# Now h1 sends the actual ip packet to the router
# Now the router decides on which interface to forward the packet to
# The decision is performed by a simple prefix match (Since gateway ip and port num is hardcoded as a table)
# Then the router needs to know the mac address of the ser. This is done again by arp
# Finally the router sends the ip packet to the ser.
# The response from server to h1 will work without arp requests because it caches the mac from previous arp requests. 

class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)

        self.switch_forwarding_table = {}

        self.routing_table = {
            "10.0.1.0/24": {
                "tos": 0,
                "interface": 1,
                "mac": "00:00:00:00:01:01",
                "gateway": "10.0.1.1"
            },
            "10.0.2.0/24": {
                "tos": 0,
                "interface": 2,
                "mac": "00:00:00:00:01:02",
                "gateway": "10.0.2.1"
            },
            "192.168.1.0/24": {
                "tos": 0,
                "interface": 3,
                "mac": "00:00:00:00:01:03",
                "gateway": "192.168.1.1"
            }
        }

        self.arp_cache = {}


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Initial flow entry for matching misses
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    # Handle the packet_in event
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath # datapath is the switch which got the packet

        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)

        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        of_proto = datapath.ofproto
        parser = datapath.ofproto_parser

        if ip_pkt: # layer 3 and above packets encountered # 
            
            self.logger.info("Executing ip logic")
            self.logger.info("src ip: %s; dst ip: %s; src mac: %s; switch id: %s; in_port: %s", ip_pkt.src, ip_pkt.dst, eth_pkt.src, datapath.id, in_port)
            self.logger.info("-------------------------------")

            self.getLayer3PacketOut(datapath, msg, ip_pkt, eth_pkt, of_proto, parser, in_port)
            # self.getLayer2PacketOut(datapath, msg, eth_pkt, of_proto, parser, in_port)
        
        elif arp_pkt: # arp discovery packet encountered
            self.logger.info("Executing arp logic")
            self.logger.info("src ip: %s; dst ip: %s; src mac: %s; switch id: %s; in_port: %s", arp_pkt.src_ip, arp_pkt.dst_ip, arp_pkt.src_mac, datapath.id, in_port)
            self.logger.info("-------------------------------")

            self.getARPPacketOut(datapath, msg, arp_pkt, eth_pkt, of_proto, parser, in_port)
            self.getLayer2PacketOut(datapath, msg, eth_pkt, of_proto, parser, in_port)
        
        else:
            self.logger.info("Executing layer 2 logic")
            self.logger.info("src mac: %s; dst mac: %s; switch id: %s; in_port: %s", eth_pkt.src, eth_pkt.dst, datapath.id, in_port)
            self.logger.info("-------------------------------")

            self.getLayer2PacketOut(datapath, msg, eth_pkt, of_proto, parser, in_port)

    def getLayer3PacketOut(self, datapath, msg, ip_pkt: ipv4.ipv4, eth_pkt, of_proto, parser, in_port):
        available_routes = self.routing_table.items()

        # The following router implementation is based on RFC 1812 (https://datatracker.ietf.org/doc/html/rfc1812#page-85)

        # The router located for matching routes in its routing table for the given ip address
        all_interfaces_for_dest = list(filter(lambda x: ipaddress.ip_address(ip_pkt.dst) in ipaddress.ip_network(x[0]), available_routes))

        # dropping packet if routing table has no matching destination entry
        if len(all_interfaces_for_dest) == 0:
            self.logger.info("No matching route found; dropping packet")
            return

        # The router finds the route with the best tos metric
        chosen_interface_for_dest = sorted(all_interfaces_for_dest, key = lambda x: x[1]["mac"])[0]
        print(chosen_interface_for_dest)
        
        try:
            mac_for_received_ip = self.arp_cache[datapath.id][ip_pkt.dst]
        except KeyError:
            self.logger.error("matching mac for ip not found; performing arp")

            if self.arp_cache.get(datapath.id) == None:
                self.arp_cache[datapath.id] = {}
            
            self.logger.info(self.arp_cache[datapath.id])
            actions = [datapath.ofproto_parser.OFPActionOutput(of_proto.OFPP_FLOOD)]

            self.send_arp_request(
                    datapath = datapath,
                    arp_type = arp.ARP_REQUEST,
                    actions = actions,
                    src_mac = chosen_interface_for_dest[1].get("mac"),
                    dst_mac = None,
                    src_ip = chosen_interface_for_dest[1].get("gateway"),
                    dst_ip = ip_pkt.dst
                )
            return
        
        e = ethernet.ethernet(chosen_interface_for_dest[1].get("mac"), mac_for_received_ip, ether_types.ETH_TYPE_IP)

        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(ip_pkt)
        p.serialize()

        actions = [parser.OFPActionOutput(chosen_interface_for_dest[1].get("interface"))]

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=0xffffffff,
            in_port=in_port,
            actions=actions,
            data=p.data)
            
        self.logger.info("Forwarding ip packet to interface: %s", chosen_interface_for_dest)
        
        datapath.send_msg(out)
    
    def send_arp_request(self, datapath, arp_type, actions, src_mac, dst_mac, src_ip, dst_ip):        
        if dst_mac == None:
            dst_mac = 'ff:ff:ff:ff:ff:ff'
        
        e = ethernet.ethernet(
                dst = dst_mac, 
                src = src_mac, 
                ethertype = ether_types.ETH_TYPE_ARP
            )
        
        a = arp.arp(
                opcode = arp_type,
                dst_mac = dst_mac,
                dst_ip = dst_ip,
                src_mac = src_mac,
                src_ip = src_ip
            )

        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()

        out = datapath.ofproto_parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=0xffffffff,
                in_port=datapath.ofproto.OFPP_CONTROLLER,
                actions=actions,
                data=p.data
            )
        
        self.logger.info("Sending arp frame: dst ip: %s", dst_ip)
        
        datapath.send_msg(out)

    def getARPPacketOut(self, datapath, msg, arp_pkt: arp.arp, eth_pkt, of_proto, parser, in_port):
        if self.arp_cache.get(datapath.id) == None:
            self.arp_cache[datapath.id] = {}
        
        self.arp_cache[datapath.id][arp_pkt.src_ip] = arp_pkt.src_mac

        self.logger.info(self.arp_cache)

        if arp_pkt.opcode == arp.ARP_REQUEST: 
            matching_subnet_info_for_ip = list(filter(lambda x: ipaddress.ip_address(arp_pkt.dst_ip) in ipaddress.ip_network(x[0]), self.routing_table.items()))[0]
            mac_for_received_ip = matching_subnet_info_for_ip[1].get("mac")

            actions = [datapath.ofproto_parser.OFPActionOutput(in_port)]

            if mac_for_received_ip == None:
                self.logger.error("Unknown ip in arp request for router")
                return

            self.send_arp_request(
                    datapath = datapath,
                    arp_type = arp.ARP_REPLY,
                    actions = actions,
                    src_mac = arp_pkt.dst_mac,
                    dst_mac = arp_pkt.src_mac,
                    src_ip = arp_pkt.dst_ip,
                    dst_ip = arp_pkt.src_ip
                )
            
        elif arp_pkt.opcode == arp.ARP_REPLY: 
            self.logger.info("arp reply received")

            self.arp_cache[datapath.id][arp_pkt.src_ip] = arp_pkt.src_mac

            self.logger.info(self.arp_cache)

            return

    def getLayer2PacketOut(self, datapath, msg, eth, of_proto, parser, in_port):
        if datapath.id not in self.switch_forwarding_table:
            self.switch_forwarding_table[datapath.id] = {}
        
        self.switch_forwarding_table[datapath.id][eth.src] = in_port

        actions = [parser.OFPActionOutput(of_proto.OFPP_FLOOD)]

        if eth.dst in self.switch_forwarding_table[datapath.id]:
            out_port = self.switch_forwarding_table[datapath.id][eth.dst]
            actions = [parser.OFPActionOutput(out_port)]

            self.logger.info("Mac found in table, routing to port: %s", out_port)

            match = parser.OFPMatch(
                in_port = in_port,
                eth_dst = eth.dst,
                eth_src = eth.src)

            self.logger.info("Added mac to flow table")
            self.add_flow(datapath, of_proto.OFP_DEFAULT_PRIORITY, match, actions)
        else:
            self.logger.info("Mac not found, flooding")

        data = None

        if msg.buffer_id == of_proto.OFP_NO_BUFFER:
            data = msg.data
        
        if data is None:
            return
        
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
    
        datapath.send_msg(out)

# ryu-manager ryu_controller.py

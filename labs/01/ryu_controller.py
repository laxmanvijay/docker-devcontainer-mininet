from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_4
from ryu.ofproto.ofproto_v1_3_parser import OFPPacketIn
from ryu import ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_4.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)

        self.switch_forwarding_table = {}
        

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

        print("enet")
        
        msg: OFPPacketIn = ev.msg
        datapath: Datapath = msg.datapath

        of_proto = datapath.ofproto

        in_port = msg.match.fields[0].value

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        self.switch_forwarding_table[eth.src] = in_port

        actions = [of_proto.OFPActionOutput(of_proto.OFPP_FLOOD)]

        if eth.dst in self.switch_forwarding_table:
            out_port = self.switch_forwarding_table[eth.dst]
            actions = [of_proto.OFPActionOutput(out_port)]

            match = of_proto.OFPMatch(
                in_port = in_port,
                eth_dst = eth.src)

            self.add_flow(datapath, of_proto.OFP_DEFAULT_PRIORITY, match, actions)

        data = None
        if msg.buffer_id == of_proto.OFP_NO_BUFFER:
            data = msg.data

        out = of_proto.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
        
        datapath.send_msg(out)
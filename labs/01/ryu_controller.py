from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

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
        msg = ev.msg
        datapath = msg.datapath # datapath is the switch which got the packet

        of_proto = datapath.ofproto
        parser = datapath.ofproto_parser

        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        self.logger.info("src mac: %s; dst mac: %s; switch id: %s", eth.src, eth.dst, datapath.id)

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

            self.logger.info("Added to flow table")
            self.add_flow(datapath, of_proto.OFP_DEFAULT_PRIORITY, match, actions)
        else:
            self.logger.info("Mac not found, flooding")

        data = None
        if msg.buffer_id == of_proto.OFP_NO_BUFFER:
            data = msg.data
        
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
        
        datapath.send_msg(out)
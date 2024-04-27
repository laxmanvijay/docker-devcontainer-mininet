from mininet.topo import Topo


class NetworkTopo(Topo):

    def __init__(self):

        Topo.__init__(self)

        h1 = self.addHost( 'h1', ip = "10.0.1.2/24", gateway = "10.0.1.1" )
        h2 = self.addHost( 'h2', ip = "10.0.1.3/24", gateway = "10.0.1.1" )
        ext = self.addHost('ext', ip = "192.168.1.123/24", gateway = "192.168.1.1")
        ser = self.addHost('ser', ip = "10.0.2.2/24", gateway = "10.0.2.1")

        s1 = self.addSwitch( 's1' )
        s2 = self.addSwitch( 's2' )
        s3 = self.addSwitch( 's3' )

        self.addLink( s1, h1, bw = 15, delay = 10 )
        self.addLink( s1, h2, bw = 15, delay = 10 )

        self.addLink( s2, ser, bw = 15, delay = 10 )

        self.addLink( s3, ext, bw = 15, delay = 10 )

        self.addLink( s3, s1 )
        self.addLink( s3, s2 )

topos = { 'mytopo': ( lambda: NetworkTopo() ) }

# service openvswitch-switch start
# mn --custom topo.py --controller remote --topo mytopo
# ryu requires eventlet 0.30.2; pip install eventlet==0.30.2 (in docker)
from mininet.topo import Topo

class NetworkTopo(Topo):

    def __init__(self):

        Topo.__init__(self)

        h1 = self.addHost( 'h1', ip = "10.0.1.2/24", defaultRoute = "via 10.0.1.1" )
        h2 = self.addHost( 'h2', ip = "10.0.1.3/24", defaultRoute = "via 10.0.1.1" )
        ext = self.addHost('ext', ip = "192.168.1.123/24", defaultRoute = "via 192.168.1.1")
        ser = self.addHost('ser', ip = "10.0.2.2/24", defaultRoute = "via 10.0.2.1")

        s1 = self.addSwitch( 's1' )
        s2 = self.addSwitch( 's2' )
        router = self.addSwitch( 's3' )

        self.addLink( s1, h1, bw = 15, delay = 10 )
        self.addLink( s1, h2, bw = 15, delay = 10 )

        self.addLink( s2, ser, bw = 15, delay = 10 )

        self.addLink( router, ext, intfName2='rt-ext', params2={ 'ip' : '192.168.1.1/24' })
        self.addLink( router, s1, intfName2='rt-s1', params2={ 'ip' : '10.0.1.1/24' } )
        self.addLink( router, s2, intfName2='rt-s2', params2={ 'ip' : '10.0.2.1/24' } )

topos = { 'mytopo': ( lambda: NetworkTopo() ) }

# service openvswitch-switch start
# mn --custom topo.py --controller remote --topo mytopo
# ryu requires eventlet 0.30.2; pip install eventlet==0.30.2 (in docker)
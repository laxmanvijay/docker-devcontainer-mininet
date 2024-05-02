from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class NetworkTopo(Topo):

    def __init__(self):

        Topo.__init__(self)

        h1 = self.addHost( 'h1', ip = "10.0.1.2/24", defaultRoute = "via 10.0.1.1" )
        h2 = self.addHost( 'h2', ip = "10.0.1.3/24", defaultRoute = "via 10.0.1.1" )
        ext = self.addHost('ext', ip = "192.168.1.123/24", defaultRoute = "via 192.168.1.1")
        ser = self.addHost('ser', ip = "10.0.2.2/24", defaultRoute = "via 10.0.2.1")

        s1 = self.addSwitch( 's1' )
        s2 = self.addSwitch( 's2' )
        s3 = self.addSwitch( 's3' )

        self.addLink( s1, h1, bw = 15, delay = 10 )
        self.addLink( s1, h2, bw = 15, delay = 10 )

        self.addLink( ser, s2, bw = 15, delay = 10 )

        self.addLink( s3, ext, intfName2='s3-ext', params2={ 'ip' : '192.168.1.1/24' })
        self.addLink( s1, s3, intfName2='s3-eth3', params2={ 'ip' : '10.0.1.1/24' } )
        self.addLink( s2, s3, intfName2='s3-eth2', params2={ 'ip' : '10.0.2.1/24' } )

def run():
    topo = NetworkTopo()
    net = Mininet(topo=topo,
                  switch=OVSKernelSwitch,
                  link=TCLink,
                  controller=None)
    net.addController(
        'c1', 
        controller=RemoteController, 
        ip="127.0.0.1", 
        port=6653)
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

# topos = { 'mytopo': ( lambda: NetworkTopo() ) }
# service openvswitch-switch start
# mn --custom topo.py --controller remote --topo mytopo if run directly
# In this case, run using python3 topo.py (run ryu controller in a separate terminal)
# To test:
# * h1 ping h2
# * pingall
# * h1 ping 10.0.1.1 -c1
# * iperf h1 h2
# ryu requires eventlet 0.30.2; pip install eventlet==0.30.2 (in docker)
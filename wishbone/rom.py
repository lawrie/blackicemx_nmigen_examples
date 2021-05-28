from nmigen import *
from nmigen_soc.memory import *
from nmigen_soc.wishbone import *

# Wishbone slave read-only memory module.
class ROM(Elaboratable, Interface):
    def __init__(self, data):

        self.data = data

        # Initialize Wishbone bus interface.
        Interface.__init__(self,
                           data_width = 16,
                           addr_width = 8)

        # Set a memory map
        #self.memory_map = MemoryMap(data_width = self.data_width,
        #                            addr_width = self.addr_width,
        #                            alignment = 0)

    def elaborate(self, platform):
        m = Module()

        # Memory and read port.
        mem = Memory(width = 11, depth = len(self.data), init = self.data)
        m.submodules.r = r = mem.read_port()

        m.d.sync += self.ack.eq(0)

        with m.If(self.cyc & self.stb):
            m.d.sync += self.ack.eq(1)

        m.d.comb += [
            r.addr.eq(self.adr),
            self.dat_r.eq(r.data)
        ]

        return m


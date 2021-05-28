from nmigen import *
from nmigen_soc.memory import *
from nmigen_soc.wishbone import *

# Wishbone slave ram memory module.
class RAM(Elaboratable, Interface):
    def __init__(self):

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

        # Memory and read and write ports.
        mem = Memory(width = 8, depth = 256)
        m.submodules.r = r = mem.read_port()
        m.submodules.w = w = mem.write_port()

        m.d.sync += self.ack.eq(0)

        with m.If(self.cyc & self.stb):
            m.d.sync += self.ack.eq(1)

        m.d.comb += [
            r.addr.eq(self.adr),
            self.dat_r.eq(r.data),
            w.data.eq(self.dat_w),
            w.addr.eq(self.adr),
            w.en.eq(self.cyc & self.we)
        ]

        return m


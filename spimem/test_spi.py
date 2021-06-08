from nmigen import *
from nmigen_boards.blackice_mx import *

from spimem import SpiMem

class Top(Elaboratable):
    def elaborate(self, platform):

        m = Module()

        csn = Signal()
        copi = Signal()
        cipo = Signal()
        sclk = Signal()
        rd   = Signal()
        wr   = Signal()
        addr = Signal(32)
        din  = Signal(8)
        dout = Signal(8)

        m.submodules.spimem = spimem = SpiMem(addr_bits=32)

        m.d.comb += [
            spimem.csn.eq(csn),
            spimem.sclk.eq(sclk),
            spimem.copi.eq(copi),
            spimem.din.eq(din),
            cipo.eq(spimem.cipo),
            addr.eq(spimem.addr),
            dout.eq(spimem.dout),
            rd.eq(spimem.rd),
            wr.eq(spimem.wr)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Top(), do_program=True)


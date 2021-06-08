from nmigen import *
from nmigen_boards.blackice_mx import *

from spimem import SpiMem

class Top(Elaboratable):
    def elaborate(self, platform):
        csn = platform.request("dcs")
        sclk = platform.request("dsck")
        copi = platform.request("dd0")
        cipo = platform.request("dd1", dir="-")

        m = Module()

        rd   = Signal()
        wr   = Signal()
        addr = Signal(32)
        din  = Signal(8)
        dout = Signal(8)

        m.submodules.spimem = spimem = SpiMem(addr_bits=16)

        mem = Memory(width=8, depth=4 * 1024)
        m.submodules.r = r = mem.read_port()
        m.submodules.w = w = mem.write_port()

        m.d.comb += [
            spimem.csn.eq(csn),
            spimem.sclk.eq(sclk),
            spimem.copi.eq(copi),
            spimem.din.eq(din),
            cipo.eq(spimem.cipo),
            addr.eq(spimem.addr),
            dout.eq(spimem.dout),
            rd.eq(spimem.rd),
            wr.eq(spimem.wr),
            r.addr.eq(addr),
            din.eq(r.data),
            w.data.eq(dout),
            w.addr.eq(addr),
            w.en.eq(wr)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Top(), do_program=True)


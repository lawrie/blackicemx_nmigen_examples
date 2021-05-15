from nmigen import *
from math import ceil, log2

class TextLCD(Elaboratable):
    def __init__(self):
        # inputs
        self.valid = Signal()
        # outputs
        self.e     = Signal(reset=0)
        self.ready = Signal(reset=1)

    def elaborate(self, platform):
        m = Module()

        CLK_MHZ = int(platform.default_clk_frequency/1000000)
        
        E_CLKS = ceil(.22 * CLK_MHZ) # 220 ns
        print("E_CLKS:", E_CLKS)

        COUNT_BITS = ceil(log2(E_CLKS +1))
        print("count bits:", COUNT_BITS)

        count = Signal(COUNT_BITS, reset=0)

        with m.If(self.valid):
            m.d.sync += [
                count.eq(1),
                self.ready.eq(0),
                self.e.eq(1)
            ]

        with m.If(count == E_CLKS):
            m.d.sync += [
                count.eq(0),
                self.e.eq(0),
                self.ready.eq(1) # One extra clock cycle before ready
            ]
        with m.Elif(count > 0):
            m.d.sync += count.eq(count + 1)

        return m


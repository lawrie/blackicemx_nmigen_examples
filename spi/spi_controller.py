from nmigen import *
from nmigen.utils import bits_for
from nmigen.lib.cdc import FFSynchronizer

from math import ceil, log2

class SpiController(Elaboratable):
    def __init__(self, *, divisor=1, divisor_bits=None, data_bits=8, use_csn=True, pins=None):
        # parameters
        self.data_bits = data_bits # Currently must be a power 0f 2
        self._pins = pins
        self.use_csn = use_csn

        # inputs
        self.cipo    = Signal(reset=1)
        self.din     = Signal(data_bits)
        self.req     = Signal(reset=0)
        self.divisor = Signal(divisor_bits or bits_for(divisor), reset=divisor)
        self.mode    = Signal(2, reset=0)

        # outputs
        self.csn     = Signal(reset=1)
        self.copi    = Signal(reset=0)
        self.sclk    = Signal(reset=0)
        self.dout    = Signal(data_bits, reset = 0)
        self.done    = Signal(reset=0)
        self.rdy     = Signal(reset=1)

    def elaborate(self, platform):
        m = Module()

        STATE_BITS = ceil(log2(self.data_bits * 2)) + 1

        div_cnt = Signal.like(self.divisor)
        state   = Signal(STATE_BITS, reset=0)
        data     = Signal(self.data_bits)

        cpol    = Signal()
        cpha    = Signal()

        m.d.comb += [
            cpol.eq(self.mode[1]),
            cpha.eq(self.mode[0])
        ]

        if self._pins is not None:
            if self.use_csn:
                m.d.comb += self.pins.cs_n.o.eq(self.cs_n)
            m.d.comb += self.pins.copi.o.eq(self.copi)
            m.d.comb += self.pins.clk.o.eq(self.sclk)
            m.submodules += FFSynchronizer(self._pins.cipo, self.cipo, reset=1)

        m.d.sync += [
            self.done.eq(0),
            self.rdy.eq(1)
        ]

        with m.If(self.req | ~self.rdy):
            m.d.sync += [
                # Set rdy false when active
                self.rdy.eq(0),
                # Toggle sclk according to cpha and cpol
                self.sclk.eq((state[0] ^ cpha) ^ cpol),
                # Clock divider
                div_cnt.eq(Mux(div_cnt == self.divisor - 1, 0, div_cnt + 1))
            ]

            # Set pins when divisor count goes to zero
            with m.If(div_cnt == 0):
                with m.If(state == 0):
                    m.d.sync += [
                        # Start of transaction
                        self.copi.eq(self.din[-1]),
                        data.eq(self.din)
                    ]
                    if self.use_csn:
                        m.d.sync += self.csn.eq(0)
                with m.Else():
                    # Shift the data out and in
                    with m.If(state[0]):
                        m.d.sync += data.eq(Cat(self.cipo, data[:-1:]))
                    with m.Elif(~state[-1]):
                        m.d.sync += self.copi.eq(data[-1])

            with m.If(div_cnt == self.divisor -1):
                with m.If(Mux(cpha, state == (self.data_bits * 2) - 1, state == self.data_bits * 2)):
                    m.d.sync += [
                        # End of transaction
                        self.done.eq(1),
                        self.rdy.eq(1),
                        self.dout.eq(data),
                        state.eq(0)
                    ]
                    if self.use_csn:
                        m.d.sync += self.csn.eq(1)
                with m.Else():
                    # Increment state
                    m.d.sync += state.eq(state + 1)

        return m


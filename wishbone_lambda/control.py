from nmigen import *

from nmigen_soc import wishbone
from nmigen_soc.memory import MemoryMap

from lambdasoc.periph import Peripheral

class ControlPeripheral(Peripheral, Elaboratable):
    """CPU Control Peripheral
    Parameters
    ----------
    data_width : int
        Bus data width.
    granularity : int
        Bus granularity.
   
    Attributes
    ----------
    bus : :class:`nmigen_soc.wishbone.Interface`
        Wishbone bus interface.

    halt : Signal()
         Halt the cpu
    reset: Signal()
         Reset the CPU

    """
    def __init__(self, data_width=32, granularity=8):
        super().__init__()

        self.reset = Signal(reset=0)
        self.halt  = Signal(reset=0)

        self.bus = wishbone.Interface(addr_width=1,
                                      data_width=data_width, granularity=granularity,
                                      features={"cti", "bte"})

        map = MemoryMap(addr_width=1, data_width=granularity)
        self.bus.memory_map = map

    def elaborate(self, platform):
        m = Module()

        with m.If(self.bus.ack):
            m.d.sync += self.bus.ack.eq(0)

        with m.If(self.bus.cyc & self.bus.stb):
            m.d.sync += self.bus.ack.eq(1)

            with m.If(self.bus.adr == 0):
                m.d.sync += self.reset.eq(self.bus.dat_w)
                m.d.comb += self.bus.dat_r.eq(self.reset)
            with m.Else():
                m.d.sync += self.halt.eq(self.bus.dat_w)
                m.d.comb += self.bus.dat_r.eq(self.halt)

        return m

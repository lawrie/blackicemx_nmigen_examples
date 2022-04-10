from nmigen import *

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

    CSR registers
    -------------
    halt : rw
         Halt the cpu
    reset: rw
         Reset the CPU

    """
    def __init__(self, data_width=32, granularity=8):
        super().__init__()

        bank = self.csr_bank()
        self.reset = bank.csr(1,"rw")
        self.halt  = bank.csr(1,"rw")

        self._bridge = self.bridge(data_width=data_width, granularity=granularity)

        self.bus = self._bridge.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge = self._bridge

        with m.If(self.reset.w_stb):
            m.d.sync += self.reset.r_data.eq(self.reset.w_data)

        with m.If(self.halt.w_stb):
            m.d.sync += self.halt.r_data.eq(self.halt.w_data)

        return m


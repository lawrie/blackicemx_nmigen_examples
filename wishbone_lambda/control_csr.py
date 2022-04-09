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

        self._bridge = self.bridge(data_width=data_width, granularity=granularity, alignment=2)

        self.bus = self._bridge.bus

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge = self._bridge

        return m


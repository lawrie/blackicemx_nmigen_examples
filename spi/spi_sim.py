from nmigen import *
from nmigen.sim import *
from spi_controller import SpiController
 
if __name__ == "__main__":
    def process():
        for i in range(1):
            yield dut.din.eq(0xc3)
            yield dut.req.eq(1)
            yield dut.mode.eq(0)
            yield
            yield dut.req.eq(0)
            while True:
                yield
                done = yield dut.done
                if done:
                    break

    m = Module()
    dut = SpiController(use_csn=True, divisor=2)
    m.submodules.dut = dut

    sim = Simulator(m) 
    sim.add_clock(1e-6)
    sim.add_sync_process(process)
    with sim.write_vcd("test.vcd", "test.gtkw"):
        sim.run()


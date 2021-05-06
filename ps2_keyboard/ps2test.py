from nmigen import *
from nmigen_boards.blackice_mx import *

from uart import *
from ps2 import *

pmod_ps2 = [
    Resource("PS2",0,
             Subsignal("ps2_clk", Pins("3", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("ps2_data", Pins("1", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class ByteToHex(Elaboratable):
    def __init__(self):
        self.b = Signal(4)
        self.h = Signal(8)

    def elaborate(self, platform):
        
        m = Module()

        with m.If(self.b < 10):
            m.d.comb += self.h.eq(ord('0') + self.b)
        with m.Else():
            m.d.comb += self.h.eq(ord('a') + self.b - 10)

        return m
        
class Ps2Test(Elaboratable):
    def elaborate(self, platform):
        led   = [platform.request("led", i) for i in range(4)]
        leds  = Cat([led[i].o for i in range(4)])
        serial = platform.request("uart")
        ps2_pmod = tp = platform.request("PS2")
        m = Module()

        uart = UART(serial, int(platform.default_clk_frequency), 115200)
        m.submodules.uart = uart

        ps2 = PS2()
        m.submodules.ps2 = ps2

        bytetohex = ByteToHex()
        m.submodules.bytetohex = bytetohex

        tx_ready = Signal(1, reset=0)
        tx_state = Signal(2, reset=0)

        m.d.comb += [
            ps2.ps2_clk.eq(ps2_pmod.ps2_clk),
            ps2.ps2_data.eq(ps2_pmod.ps2_data),
            leds.eq(ps2.data),
            uart.tx_ready.eq(tx_ready),
            uart.tx_data.eq(bytetohex.h)
        ]

        with m.Switch(tx_state):
            with m.Case(0):
                with m.If(ps2.valid):
                    m.d.sync += [
                        tx_state.eq(1),
                        bytetohex.b.eq(ps2.data[4:]),
                        tx_ready.eq(1)
                    ]
            with m.Case(1):
                with m.If(uart.tx_ack):
                    m.d.sync += [
                         tx_state.eq(2),
                         bytetohex.b.eq(ps2.data[:4])
                    ]
            with m.Case(2):
                with m.If(uart.tx_ack):
                    m.d.sync += [
                        tx_state.eq(0),
                        tx_ready.eq(0)
                    ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(pmod_ps2)
    platform.build(Ps2Test(), do_program=True)

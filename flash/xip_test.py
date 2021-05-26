from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from xip_controller import XipController

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        leds8 = Cat([i for i in platform.request("leds8_1")])

        m = Module()

        m.submodules.xip = xip = XipController(width=8)

        state = Signal(3, reset=0)

        # Applies to odd states. Unset valid when transaction accepted
        with m.If(xip.ready):
            m.d.sync += xip.valid.eq(0)

        # Applies to odd states. Display data and move on when data is valid
        with m.If(xip.dout_valid):
            m.d.sync += [
                leds8.eq(xip.dout),
                state.eq(state+1)
            ]

        # Send a couple of requests (on even state numbers)
        with m.Switch(state):
            with m.Case(0):
                m.d.sync += [
                    xip.addr.eq(0),
                    xip.valid.eq(1),
                    state.eq(state+1)
                ]
            with m.Case(2):
                m.d.sync += [
                    xip.addr.eq(2),
                    xip.valid.eq(1),
                    state.eq(state+1)
                ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)

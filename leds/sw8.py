from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

switch_pmod = [
    Resource("sw8", 0,
             Subsignal("sw", Pins("7 8 9 10 1 2 3 4", dir="i", conn=("pmod", 5)), Attrs(IO_STANDARD="LVCMOS3")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        leds8_1 = platform.request("leds8_1")
        leds8 = Cat([i for i in leds8_1.leds])
        sw8 = platform.request("sw8")
        sws8 = Cat([i for i in sw8.sw])

        m = Module()

        m.d.comb += leds8.eq(sws8)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.add_resources(switch_pmod)
    platform.build(Top(), do_program=True)


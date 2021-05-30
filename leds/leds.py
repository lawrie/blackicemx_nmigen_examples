from nmigen import *
from nmigen_boards.blackice_mx import *

class Leds(Elaboratable):
    def elaborate(self, platform):
        leds  = Cat([platform.request("led", i) for i in range(4)])
        timer = Signal(26)

        m = Module()
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += leds.eq(timer[-5:-1])
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Leds(), do_program=True)


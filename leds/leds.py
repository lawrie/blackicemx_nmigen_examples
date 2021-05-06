from nmigen import *
from nmigen_boards.blackice_mx import *

class Leds(Elaboratable):
    def elaborate(self, platform):
        led   = [platform.request("led", i) for i in range(4)]
        timer = Signal(30)

        m = Module()
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += Cat([i.o for i in led]).eq(timer[-9:-1])
        return m


if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Leds(), do_program=True)

from nmigen import *
from nmigen_boards.blackice_mx import *

from debouncer import Debouncer

class Debounce(Elaboratable):
    def elaborate(self, platform):
        leds  = Cat([platform.request("led", i) for i in range(1,4)])
        btn1 = platform.request("button", 0)

        m = Module()

        m.submodules.debouncer = debouncer = Debouncer()

        m.d.comb += debouncer.btn.eq(btn1)

        with m.If(debouncer.btn_up):
            m.d.sync += leds.eq(leds+1)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Debounce(), do_program=True)

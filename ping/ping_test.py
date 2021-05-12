from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from ping import Ping
from debouncer import Debouncer

ping_pmod = [
    Resource("ping", 0,
             Subsignal("trig", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("echo", Pins("2", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        led  = [platform.request("led", i) for i in range(1,4)]
        btn1 = platform.request("button", 0)
        leds = Cat([led[i].o for i in range(3)])
        png = platform.request("ping")
        leds8_1 = platform.request("leds8_1")
        led8 =  [i for i in leds8_1]
        leds8 = Cat([i for i in led8])

        m = Module()

        debouncer = Debouncer()
        m.submodules.debouncer = debouncer

        m.d.comb += debouncer.btn.eq(btn1)

        m.submodules.ping = ping = Ping()

        m.d.comb += [
            png.trig.eq(ping.trig),
            ping.echo.eq(png.echo),
            ping.req.eq(debouncer.btn_down),
            leds[0].eq(ping.done),
            leds[2].eq(ping.val.all()),
            leds8.eq(ping.val)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(ping_pmod)
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)


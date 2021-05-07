from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *
from seven_seg import SevenSegController

seven_seg_pmod = [
    Resource("seven_seg", 0,
            Subsignal("aa", Pins("7", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ab", Pins("8", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ac", Pins("9", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ad", Pins("10", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ae", Pins("7", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("af", Pins("8", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ag", Pins("9", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ca", Pins("10", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class SevenTest(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(4)]
        seg_pins = platform.request("seven_seg")

        timer = Signal(28)
        seven = SevenSegController()

        m = Module()
        m.submodules.seven = seven
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += [
            Cat([i.o for i in led]).eq(timer[-9:-1]),
            Cat([seg_pins.aa, seg_pins.ab, seg_pins.ac, seg_pins.ad,
                 seg_pins.ae, seg_pins.af, seg_pins.ag]).eq(seven.leds),
            seg_pins.ca.eq(timer[-1])
        ]
             
        m.d.comb += seven.val.eq(timer[-5:-1])

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(seven_seg_pmod)
    platform.build(SevenTest(), do_program=True)

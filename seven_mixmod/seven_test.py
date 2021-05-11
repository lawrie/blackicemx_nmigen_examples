from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *
from seven_seg import SevenSegController

seven_seg_mixmod = [
    Resource("seven_seg", 0,
            Subsignal("a",  Pins("27", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("b",  Pins("28", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("c",  Pins("26", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("d",  Pins("25", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("e",  Pins("10", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("f",  Pins("13", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("g",  Pins("12", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("dp", Pins("11", invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ca", Pins("4 19 18",  invert=True, dir="o", conn=("mixmod",1)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class SevenTest(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(4)]
        seg_pins = platform.request("seven_seg")

        timer = Signal(29)
        seven = SevenSegController()

        m = Module()
        m.submodules.seven = seven
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += [
            Cat([i.o for i in led]).eq(timer[-9:-1]),
            Cat([seg_pins.a, seg_pins.b, seg_pins.c, seg_pins.d,
                 seg_pins.e, seg_pins.f, seg_pins.g]).eq(seven.leds),
        ]
             
        for i in range(3):
            m.d.comb += seg_pins.ca[i].eq(timer[-3:-1] == i)

        m.d.comb += seven.val.eq(timer[-7:-3])

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(seven_seg_mixmod)
    platform.build(SevenTest(), do_program=True)


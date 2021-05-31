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
        # Get pins
        seg_pins = platform.request("seven_seg")
        leds7 = Cat([seg_pins.a, seg_pins.b, seg_pins.c, seg_pins.d,
                     seg_pins.e, seg_pins.f, seg_pins.g])

        # Add 7-segment controller
        m = Module()
        m.submodules.seven = seven = SevenSegController()

        # Timer
        timer = Signal(40)
        m.d.sync += timer.eq(timer + 1)


        # Connect pins
        m.d.comb += [
            leds7.eq(seven.leds)
        ]
             
        # Set pins for each digit to appropriate slice of time to count up in hex
        for i in range(3):
            # Each digit refreshed at at least 100Hz
            m.d.comb += seg_pins.ca[i].eq(timer[17:19] == i)

            with m.If(seg_pins.ca[i]):
                m.d.comb += seven.val.eq(timer[((i - 3) * 4) - 5:((i - 3) * 4) - 1])

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(seven_seg_mixmod)
    platform.build(SevenTest(), do_program=True)


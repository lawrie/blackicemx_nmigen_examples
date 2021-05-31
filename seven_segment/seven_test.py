from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *
from seven_seg import SevenSegController

seven_seg_pmod = [
    Resource("seven_seg", 0,
            Subsignal("aa", Pins("7",  dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ab", Pins("8",  dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ac", Pins("9",  dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ad", Pins("10", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ae", Pins("7",  dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("af", Pins("8",  dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ag", Pins("9",  dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("ca", Pins("10", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class SevenTest(Elaboratable):
    def elaborate(self, platform):
        # Get pins
        seg_pins = platform.request("seven_seg")
        leds7 = Cat([seg_pins.aa, seg_pins.ab, seg_pins.ac, seg_pins.ad,
                     seg_pins.ae, seg_pins.af, seg_pins.ag])

        # Add 7-segment controller
        m = Module()
        m.submodules.seven = seven = SevenSegController()

        # Timer
        timer = Signal(32)
        m.d.sync += timer.eq(timer + 1)

        # Connect pins 
        m.d.comb += [
            leds7.eq(seven.leds),
            # Each digit refreshed at 100Hz
            seg_pins.ca.eq(timer[18])
        ]
    
        # Set digits to 4-bit slices of timer, to count up
        m.d.comb += seven.val.eq(Mux(timer[18], timer[-5:-1], timer[-9:-5]))

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(seven_seg_pmod)
    platform.build(SevenTest(), do_program=True)


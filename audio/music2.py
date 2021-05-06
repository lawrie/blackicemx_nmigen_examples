from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("l", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Music2(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")

        m = Module()

        left = audio.l
        clkdivider = int(platform.default_clk_frequency / 440 / 2)
        counter = Signal(clkdivider.bit_length())
        tone = Signal(24)

        m.d.comb += audio.shutdown.eq(1)
        m.d.sync += tone.eq(tone + 1)

        with m.If(counter == 0):
           m.d.sync += left.eq(15 - left)
           with m.If(tone[-1]):
               m.d.sync += counter.eq(clkdivider - 1)
           with m.Else():
               m.d.sync += counter.eq(int(clkdivider / 2) - 1)
        with m.Else():
           m.d.sync += counter.eq(counter - 1)
          
        return m


if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(audio_pmod)
    platform.build(Music2(), do_program=True)

from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",      Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Music2a(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")

        m = Module()

        counter = Signal(15)
        clkdivider = Signal(15)
        tone = Signal(28)
        fastsweep = Signal(7)
        slowsweep = Signal(7)

        m.d.comb += audio.shutdown.eq(1)
        m.d.sync += tone.eq(tone + 1)

        with m.If(tone[22]):
            m.d.comb += fastsweep.eq(tone[15:22])
        with m.Else():
            m.d.comb += fastsweep.eq(~tone[15:22])

        with m.If(tone[25]):
            m.d.comb += slowsweep.eq(tone[18:25])
        with m.Else():
            m.d.comb += slowsweep.eq(~tone[18:25])

        with m.If(tone[27]):
            m.d.comb += clkdivider.eq(Cat([Const(0,6),slowsweep,Const(1,2)]))
        with m.Else():
            m.d.comb += clkdivider.eq(Cat([Const(0,6),fastsweep,Const(1,2)]))

        with m.If(counter == 0):
            m.d.sync += [
                audio.ain.eq(~audio.ain),
                counter.eq(clkdivider)
            ]
        with m.Else():
           m.d.sync += counter.eq(counter - 1)
          
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(audio_pmod)
    platform.build(Music2a(), do_program=True)


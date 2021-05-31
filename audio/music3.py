from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from divideby12 import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",      Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Music3(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")

        m = Module()

        notes = [512,483,456,431,406,384,362,342,323,304,287,271]
        notemem = Memory(width=9, depth=16, init=map(lambda x: x -1, notes))

        octave = Signal(3)
        note = Signal(4)
        fullnote = Signal(6)
        counter_note = Signal(9)
        counter_octave = Signal(8)
        clkdivider = Signal(11)
        tone = Signal(28)

        m.d.comb += audio.shutdown.eq(1)

        divby12 = DivideBy12()
        m.submodules.divby12 = divby12

        m.d.comb += [
            divby12.numer.eq(fullnote),
            octave.eq(divby12.quotient),
            note.eq(divby12.remain),
            fullnote.eq(tone[22:]),
            clkdivider.eq(Cat([Const(0,2), notemem[note]]))
        ]

        m.d.sync += tone.eq(tone + 1)

        with m.If(counter_note == 0):
            m.d.sync += counter_note.eq(clkdivider)
            with m.If(counter_octave == 0):
                m.d.sync += audio.ain.eq(~audio.ain)
                with m.If(octave == 0):
                    m.d.sync += counter_octave.eq(255)
                with m.Elif(octave == 1):
                    m.d.sync += counter_octave.eq(127)
                with m.Elif(octave == 2 ):
                    m.d.sync += counter_octave.eq(63)
                with m.Elif(octave == 3):
                    m.d.sync += counter_octave.eq(31)
                with m.Elif(octave == 4):
                    m.d.sync += counter_octave.eq(15)
                with m.Else():
                     m.d.sync += counter_octave.eq(7)
            with m.Else():
                m.d.sync += counter_octave.eq(counter_octave - 1)
        with m.Else():
            m.d.sync += counter_note.eq(counter_note - 1) 

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(audio_pmod)
    platform.build(Music3(), do_program=True)


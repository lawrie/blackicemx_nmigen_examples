from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from divideby12 import *
from readint import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",       Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Music4(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")

        m = Module()

        led = [platform.request("led", i) for i in range(4)]
        leds = Cat([i.o for i in led])

        m.d.comb += audio.shutdown.eq(1)

        notes = [512,483,456,431,406,384,362,342,323,304,287,271]
        notemem = Memory(width=9, depth=16, init=map(lambda x: x -1, notes))
        tune = readint("tune.mem")
        music_rom = Memory(width=6,depth=len(tune), init=tune)

        octave = Signal(3)
        note = Signal(4)
        fullnote = Signal(6)
        counter_note = Signal(9)
        counter_octave = Signal(8)
        clkdivider = Signal(9)
        tone = Signal(29)

        divby12 = DivideBy12()
        m.submodules.divby12 = divby12

        m.d.comb += [
            fullnote.eq(music_rom[tone[22:28]]),
            divby12.numer.eq(fullnote),
            octave.eq(divby12.quotient),
            note.eq(divby12.remain),
            clkdivider.eq(notemem[note]),
            leds.eq(fullnote)
        ]

        m.d.sync += tone.eq(tone + 1)

        with m.If(counter_note == 0):
            m.d.sync += counter_note.eq(clkdivider)
            with m.If(counter_octave == 0):
                with m.If((fullnote != 0) & (tone[28] == 0)): 
                    m.d.sync += audio.ain.eq(~audio.ain)
                m.d.sync += counter_octave.eq(255 >> octave)
            with m.Else():
                m.d.sync += counter_octave.eq(counter_octave - 1)
        with m.Else():
            m.d.sync += counter_note.eq(counter_note - 1) 

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(audio_pmod)
    platform.build(Music4(), do_program=True)


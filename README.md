# nMigen examples for Blackice MX

## Introduction

These are examples for the Blackice MX ice40 FPGA, written in the python-based nMigen HDL.

See the [nMigen Language guide](https://nmigen.info/nmigen/latest/install.html) for how to install nMigen.

You will need to install a version of [nmigen-boards](https://github.com/folknology/nmigen-boards) with Blackice MX support.

To run the blinky example on Linux, plug in your Blackice MX board and do:

```sh
export DEVICE=/dev/ttyACM0
stty -F $DEVICE raw
cd blinky
python3 blinky.py
```

You will need nextpnr-ice40 on your path.

The other examples are run in a siimilar way.

Some of the examples support simulation as well as running on the board.

The examples have been ported from a variety of sources.

## Examples

### blinky

blinky.py blinks the blue led. It demonstrsates how to synthesise a simple nMigen module on the B;ackIce MX board.

```python
from nmigen import *
from nmigen_boards.blackice_mx import *

class Blinky(Elaboratable):
    def elaborate(self, platform):
        led   = platform.request("led", 0)
        timer = Signal(24)

        m = Module()
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += led.o.eq(timer[-1])
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Blinky(), do_program=True)
```

### leds

Running leds.py counts on the 4 leds. It uses a timer that wraps round into about every second, and sets the 4 leds to the most significant bits of the timer.
You can adjust the width of the timer to set the speed.

```python
from nmigen import *
from nmigen_boards.blackice_mx import *

class Leds(Elaboratable):
    def elaborate(self, platform):
        leds  = Cat([platform.request("led", i) for i in range(4)])
        timer = Signal(26)

        m = Module()
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += leds.eq(timer[-5:-1])
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(Leds(), do_program=True)
```

leds16.py counts on 2 digilent 8-LED Pmods, connected on pmods 2 and 3.

This example shows how to define resources connected to Pmods.

```python
from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

leds8_2_pmod = [
    Resource("leds8_2", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Leds(Elaboratable):
    def elaborate(self, platform):
        leds8_1 = Cat([l for l in platform.request("leds8_1")])
        leds8_2 = Cat([l for l in platform.request("leds8_2")])
        leds16 =  Cat(leds8_1, leds8_2)
        timer = Signal(38)

        m = Module()
        m.d.sync += timer.eq(timer + 1)
        m.d.comb += leds16.eq(timer[-17:-1])
        return m


if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.add_resources(leds8_2_pmod)
    platform.build(Leds(), do_program=True)
```

ledglow.py makes all 4 leds glow using PWM.

```python
from nmigen import *
from nmigen_boards.blackice_mx import *

class LedGlow(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(4)]

        cnt       = Signal(26)
        pwm_input = Signal(4)
        pwm       = Signal(5)

        m = Module()

        m.d.sync += [
            cnt.eq(cnt + 1),
            pwm.eq(pwm[:-1] + pwm_input),
            pwm_input.eq(Mux(cnt[-1], cnt[-5:], ~cnt[-5:]))
        ]

        for l in led:
            m.d.comb += l.eq(pwm[-1])

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(LedGlow(), do_program=True)
```

### debounce

Debounces buttons.

The Debouncer is based on the one from fpga4fun.com.

```python
from nmigen import *

class Debouncer(Elaboratable):
    def __init__(self):
        self.btn       = Signal()
        self.btn_state = Signal(reset=0)
        self.btn_down  = Signal()
        self.btn_up    = Signal()

    def elaborate(self, platform):
        cnt      = Signal(15, reset=0)
        btn_sync = Signal(2,  reset=0)
        idle     = Signal()
        cnt_max  = Signal()

        m = Module()

        m.d.comb += [
            idle.eq(self.btn_state == btn_sync[1]),
            cnt_max.eq(cnt.all()),
            self.btn_down.eq(~idle & cnt_max & ~self.btn_state),
            self.btn_up.eq(~idle & cnt_max & self.btn_state)
        ]

        m.d.sync += [
            btn_sync[0].eq(~self.btn),
            btn_sync[1].eq(btn_sync[0])
        ]

        with m.If(idle):
            m.d.sync += cnt.eq(0)
        with m.Else():
            m.d.sync += cnt.eq(cnt + 1);
            with m.If (cnt_max):
                m.d.sync += self.btn_state.eq(~self.btn_state)

        return m
```

The test program, debounce.py counts up on the other 3 leds, when you press button 1, corresponding to the blue led.

```python
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
```

### seven_segment

This needs a Digilent 7-segment Pmod in the top row of pmod2 and pmod3 (the side opposite the usb connectors).

There is a separate module to set the 7-segment leds to a given hex value:

```python
from nmigen import *

class SevenSegController(Elaboratable):
    def __init__(self):
        self.val  = Signal(4)
        self.leds = Signal(7)

    def elaborate(self, platform):
        m = Module()

        table = Array([
            0b0111111, # 0
            0b0000110, # 1
            0b1011011, # 2
            0b1001111, # 3
            0b1100110, # 4
            0b1101101, # 5
            0b1111101, # 6
            0b0000111, # 7
            0b1111111, # 8
            0b1101111, # 9
            0b1110111, # A
            0b1111100, # B
            0b0111001, # C
            0b1011110, # D
            0b1111001, # E
            0b1110001  # F
        ])

        m.d.comb += self.leds.eq(table[self.val])

        return m
```

And the test program, seven_test.py:

```python
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
```

Or, you can run the simulation, seven_seg_sim.py

```python
from nmigen import *
from nmigen.sim import *
from seven_seg import SevenSegController

def print_seven(leds):
    line_top = ["   ", " _ "]
    line_mid = ["   ", "  |", " _ ", " _|", "|  ", "| |", "|_ ", "|_|"]
    line_bot = line_mid

    a = leds & 1
    fgb = ((leds >> 1) & 1) | ((leds >> 5) & 2) | ((leds >> 3) & 4)
    edc = ((leds >> 2) & 1) | ((leds >> 2) & 2) | ((leds >> 2) & 4)

    print(line_top[a])
    print(line_mid[fgb])
    print(line_bot[edc])


if __name__ == "__main__":
    def process():
        for i in range(16):
            yield dut.val.eq(i)
            yield Delay()
            print_seven((yield dut.leds))
    dut = SevenSegController()
    sim = Simulator(dut)
    sim.add_process(process)
    sim.run()
```

The two digit Dilgilent 7-segment Pmod has pins for driving just one 7-segment digit, and another pin (ca) selects which digit is active. To display values on both digits, you need to switch between each digit and display the required value on each digit at least one hundred times a second, so that the digits appear to be permanently lit.

### seven_mixmod

This needs a Mystorm 7-segment Mixmod connected on mixmod 1.

Both seven_seg.py and seven_seg_sim.py are the same as for the Digilent Pmod, but the Mixmod has 3 digits, and a different mapping to pins, so seven_test.py is changed:

```python
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
```

The 7-segment Mixmod has three digits and has an array of 3 ca pins for selecting each digit.

### uart

uart_test.py uses the nmigen-stdio Serial class to echo characters.

```
from nmigen import *
from nmigen_stdio.serial import *

from nmigen_boards.blackice_mx import *

class UartTest(Elaboratable):
    def elaborate(self, platform):

        uart    = platform.request("uart")
        leds    = Cat([platform.request("led", i) for i in range(4)])
        divisor = int(platform.default_clk_frequency // 115200)

        m = Module()

        # Create the uart
        m.submodules.serial = serial = AsyncSerial(divisor=divisor, pins=uart)

        m.d.comb += [
            # Connect data out to data in
            serial.tx.data.eq(serial.rx.data),
            # Always allow reads
            serial.rx.ack.eq(1),
            # Write data when received
            serial.tx.ack.eq(serial.rx.rdy),
            # Show any errors on leds: red for parity, green for overflow, blue for frame
            leds.eq(Cat(serial.rx.err.frame, serial.rx.err.overflow, 0b0, serial.rx.err.parity))
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(UartTest(), do_program=True)
```

### audio

These are audio examples from [fpga4fun.com](https://www.fpga4fun.com/MusicBox.html).

They are set up for [Digilent Amp2 Pmod](https://store.digilentinc.com/pmod-amp2-audio-amplifier/) in the bottom row of pmod 5 (next to the usb connector), but you can just connect a speaker or earphones to pin 19.

All these examples use a very simple way of generating tones on the audio output pin. They just generate a square wave by reversing the pin polarity at the required frequency.

More complex waveforms can be generated by using pulse density modulation, but that is beyond the scope of these examples.

music1.py plays middle C:

```python
from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",      Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Music1(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")

        m = Module()

        clkdivider = int(platform.default_clk_frequency / 440 / 2)
        counter = Signal(clkdivider.bit_length())

        m.d.comb += audio.shutdown.eq(1)

        with m.If(counter == 0):
           m.d.sync += [
               counter.eq(clkdivider - 1),
               audio.ain.eq(~audio.ain)
           ]
        with m.Else():
           m.d.sync += counter.eq(counter - 1)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(audio_pmod)
    platform.build(Music1(), do_program=True)
```

music2.py plays 2 tones alternating:

```python
from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",      Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Music2(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")

        m = Module()

        clkdivider = int(platform.default_clk_frequency / 440 / 2)
        counter = Signal(clkdivider.bit_length())
        tone = Signal(24)

        m.d.comb += audio.shutdown.eq(1)
        m.d.sync += tone.eq(tone + 1)

        with m.If(counter == 0):
           m.d.sync += audio.ain.eq(~audio.ain)
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
```

music2a.py plays a siren:

```python
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
```

music3.py plays a scale. It uses a divideby12 module:

```python
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
```

music4.py plays a tune. It uses a readint function to read the tune from a file:

```python
from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from divideby12 import *
from readint import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",      Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
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
```

### servo

This example drives a servo motor. It needs the [Digilent Servo Pmod](https://store.digilentinc.com/pmod-con3-r-c-servo-connectors/).

Servo motors are controlled by specifying a required angle for the spindle to be held at. The angle is determined by a pulse on a single digit output: the length of the pulse specifies the angle. Pulses must be sent at least 50 times a second (every 20 milliseconds) to maintain the output. A zero value usually corresponds to a pulse of 1.5 milliseconds, with a 90 degree change of angle (plus or minus) to 0.5 milliseconds, so a 1 ms pulse means -90 degrees and 2 ms means +90 degrees. But the exact values for a specific mtor need to be calibtated.

servo.py is the Servo controller:

```python
from nmigen import *

from nmigen.utils import bits_for

class Servo(Elaboratable):
    def __init__(self):
        # inputs
        self.on        = Signal()
        self.angle     = Signal(signed(8))

        # output
        self.out       = Signal()

    def elaborate(self, platform):

        clk_freq          = int(platform.default_clk_frequency)
        cycles_per_pulse  = int(clk_freq // 50) # 20ms
        cnt_bits          = bits_for(cycles_per_pulse)
        cycles_per_degree = C(int((cycles_per_pulse // 40) // 90), cnt_bits)
        zero_point        = C(int((cycles_per_pulse // 40) * 3), cnt_bits) # 1.5ms
        print("cycles per pulse:", cycles_per_pulse)
        print("cycles per degree:", cycles_per_degree)
        print("zero point:", zero_point)

        cnt = Signal(cnt_bits, reset=0)

        m = Module()

        with m.If(self.on):
            m.d.sync += cnt.eq(cnt + 1)
            with m.If(cnt == (cycles_per_pulse - 1)):
                m.d.sync += [
                    cnt.eq(0),
                    self.out.eq(1)
                ]
            with m.Elif(cnt == (zero_point + (self.angle * cycles_per_degree))):
                m.d.sync += self.out.eq(0)
        with m.Else():
            m.d.sync += self.out.eq(0)

        return m
```

Run servo_test.py for a very simple test:

```python
from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from servo import Servo

servo_pmod= [
    Resource("servo", 0,
            Subsignal("p1", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("p2", Pins("2", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("p3", Pins("3", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("p4", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        servo_pins = platform.request("servo")

        m = Module()

        m.submodules.servo = servo = Servo()

        m.d.comb += [
            servo.on.eq(1),
            servo_pins.p1.eq(servo.out),
            servo.angle.eq(120)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(servo_pmod)
    platform.build(Top(), do_program=True)
```

### ps2_keyboard

This needs a Digilent PS/2 keyboard Pmod connected to the bottom row of pmod5.

This is the PS/2 keyboard controller, ps2.v:

```python
from nmigen import *

class PS2(Elaboratable):
    def __init__(self):
        self.ps2_clk  = Signal(1)
        self.ps2_data = Signal(1)
        self.data     = Signal(8, reset=0)
        self.valid    = Signal(1, reset=0)
        self.error    = Signal(1, reset=0)

    def elaborate(self, platform):
        clk_filter  = Signal(8, reset=0xff)
        ps2_clk_in  = Signal(1, reset=1)
        ps2_data_in = Signal(1, reset=1)
        clk_edge    = Signal(1, reset=0)
        bit_count   = Signal(4, reset=0)
        shift_reg   = Signal(9, reset=0)
        parity      = Signal(1, reset=0)

        m = Module()

        m.d.sync += [
            ps2_data_in.eq(self.ps2_data),
            clk_filter.eq(Cat(clk_filter[1:], self.ps2_clk)),
            clk_edge.eq(0)
        ]

        with m.If(clk_filter.all()):
            m.d.sync += ps2_clk_in.eq(1)
        with m.Elif(clk_filter == 0):
            with m.If(ps2_clk_in):
                m.d.sync += clk_edge.eq(1)
            m.d.sync += ps2_clk_in.eq(0)

        m.d.sync += [
            self.valid.eq(0),
            self.error.eq(0)
        ]

        with m.If(clk_edge):
           with m.If(bit_count == 0):
               m.d.sync += parity.eq(0)
               with m.If(~ps2_data_in):
                   m.d.sync += bit_count.eq(bit_count + 1)
           with m.Else():
               with m.If(bit_count < 10):
                   m.d.sync += [
                       bit_count.eq(bit_count + 1),
                       shift_reg.eq(Cat([shift_reg[1:],ps2_data_in])),
                       parity.eq(parity ^ ps2_data_in)
                   ]
               with m.Elif(ps2_data_in):
                   m.d.sync += bit_count.eq(0)
                   with m.If(parity):
                       m.d.sync += [
                           self.data.eq(shift_reg[:8]),
                           self.valid.eq(1)
                       ]
                   with m.Else():
                       m.d.sync += self.error.eq(1)
               with m.Else():
                    m.d.sync += [
                        bit_count.eq(0),
                        self.error.eq(1)
                    ]

        return m
```

When you press a key on the keyboard the scan codes are written in hex to the uart, so run `cat $DEVICE`.

### vga

This nMigen VGA implementation is based on the DVI implementation on the Ulx3s board by [Guztech](https://github.com/GuzTech/ulx3s-nmigen-examples/tree/master/dvi).

It needs the Digilent VGA Pmod in pmods 2 and 3, opposite the usb connectors.

VGA timings for various resolutions are in vga_timings.py:

```python
from typing import NamedTuple


class VGATiming(NamedTuple):
    x: int
    y: int
    refresh_rate: float
    pixel_freq: int
    h_front_porch: int
    h_sync_pulse: int
    h_back_porch: int
    v_front_porch: int
    v_sync_pulse: int
    v_back_porch: int

vga_timings = {

...

    '1024x768@60Hz': VGATiming(
        x             = 1024,
        y             = 768,
        refresh_rate  = 60.0,
        pixel_freq    = 65_000_000,
        h_front_porch = 24,
        h_sync_pulse  = 136,
        h_back_porch  = 160,
        v_front_porch = 3,
        v_sync_pulse  = 6,
        v_back_porch  = 29),

...

}
```

Just one of the timings is shown; there are many others in the file including the standard vga 640x480@60Hz.

The vga implementation is in vga.py, and its interface is:

```python
class VGA(Elaboratable):
    def __init__(self,
                 resolution_x      = 640,
                 hsync_front_porch = 16,
                 hsync_pulse       = 96,
                 hsync_back_porch  = 48, #44,
                 resolution_y      = 480,
                 vsync_front_porch = 10,
                 vsync_pulse       = 2,
                 vsync_back_porch  = 33, #31,
                 bits_x            = 10, # should fit resolution_x + hsync_front_porch + hsync_pulse + hsync_back_porch
                 bits_y            = 10, # should fit resolution_y + vsync_front_porch + vsync_pulse + vsync_back_porch
                 dbl_x             = False,
                 dbl_y             = False):
        self.i_clk_en       = Signal()
        self.i_test_picture = Signal()
        self.i_r            = Signal(8)
        self.i_g            = Signal(8)
        self.i_b            = Signal(8)
        self.o_fetch_next   = Signal()
        self.o_beam_x       = Signal(bits_x)
        self.o_beam_y       = Signal(bits_y)
        self.o_vga_r        = Signal(8)
        self.o_vga_g        = Signal(8)
        self.o_vga_b        = Signal(8)
        self.o_vga_hsync    = Signal()
        self.o_vga_vsync    = Signal()
        self.o_vga_vblank   = Signal()
        self.o_vga_blank    = Signal()
        self.o_vga_de       = Signal()
        # Configuration
        self.resolution_x     = resolution_x
        self.hsync_front_port = hsync_front_porch
        self.hsync_pulse      = hsync_pulse
        self.hsync_back_porch = hsync_back_porch
        self.resolution_y     = resolution_y
        self.vsync_front_port = vsync_front_porch
        self.vsync_pulse      = vsync_pulse
        self.vsync_back_porch = vsync_back_porch
        self.bits_x           = bits_x
        self.bits_y           = bits_y
```

To run the pixel clock at the speed specified by the timings, a PLL is needed. In top_vgatest.py, the PLL is set up:

```python
            # Clock generator.
            m.domains.sync = cd_sync = ClockDomain("sync")
            m.d.comb += ClockSignal().eq(clk_in)

            m.submodules.pll = pll = PLL(freq_in_mhz=int(platform.default_clk_frequency / 1000000), freq_out_mhz=int(pixel_f / 1000000), domain_name="pixel")

            m.domains.pixel = cd_pixel = pll.domain
            m.d.comb += pll.clk_pin.eq(clk_in)

            #platform.add_clock_constraint(cd_sync.clk, platform.default_clk_frequency)
            platform.add_clock_constraint(cd_pixel.clk, pixel_f)
```

Run top_vgatest.py to see a pattern on the screen. By default 1024x768@60Hz mode is used.

### rotary_encoder

This needs a quadrature rotary encoder connected to pins 21 and 22.

Run rotary_encoder.py and see the leds change when yor turn the knob.


### oled

This needs a 7-pin spi ssd1331 oled display and a Pmod or other means to connect it to pmod5.

Run top_oled_vga.py to put a pattern on the display.

### st7789

This needs a 7-pin spi st7789 display and a Pmod or other means to connect it to pmod5.

The st7789 is a 240x240 color display, as opposed to the 96x64 resolution of the sdd1331, but the prices are similar.

Run st7789_test.py to get a pattern on the display.

### ws2812

Test of ws2812b leds (neopixels).

Run ws2812_test.py to test it with a 16-led neopixel ring.

### ping

Test of a 3.3v HC-SR04 ultrasonic (ping) sensor.

Run ping_test.py and press button to take a measurement.

### textlcd

This is a start of an example to drive a Hitachi HD44780 2-line text LCD.

### mitecpu

This is a [tiny 8-bit cpu](https://github.com/jbush001/MiteCPU) with a python assembler.

The least significant bits of the accumulator are mapped to the leds, so programs can flash the leds.

Assemble programs with assemble.py and run them with mitecpu.py.

The CPU has a Harvard architecture with a maximum of 256 instructions, and 256 8-bit data items. Instructions are 11 bits.
Instructions execute in 2 clock cycles, or one clock cycle if the negative edge triggers data accesses. Instructions have a 3-bit opcode and an 8 bit operand, which is usually a memory address. There are just 7 opcodes. There are three 8-bit registers: ip (instructon pointer), acc (accumulator) and index (index register).

MiteCPU is used as a wishbone master in the wishbone examples below.

### opc

This is an nmigen version of the [opc6](https://revaldinho.github.io/opc/) 16-bit one page CPU.

Assemble programs with opc6asm.py and run them with opc6_sim.py of opc_test.py.

This is just the cpu, without any connected ram or uart, so it doesn't do much.

### sdram

This is an 8-bit dual port SDRAM controller.

Run test_sdram.py to test it.

### sdram16

This is a 16-bit single port SDRAM controller.

Run test_sdram16.py to see the results on the leds: green means passed, red failed.

### ov7670

![ov7670](https://github.com/lawrie/lawrie.github.io/blob/master/images/mx_ov7670.jpg)

Reads video from an OV7670 camera, and displays it in low resolution (60x60) on an st7789 color LCD display.

Run camtest.py and press button 1 to configure the camera into RGB mode.

### ov7670_sdram

This is an SDRAM version of the OV7670 test with a 320x240 frame buffer.

Run camtest.py and press button 1 to configure the camera into RGB mode.

### ov7670_sdram_fifo

This is the start of an LCD image processor that uses a FIFO to avoid contention on the SDRAM when reading pixels from the camera and writing them to the LCD.

### flash

flash_test.py reads the flash memory and displays it on leds one byte at a time, each second.

It needs a Digilent 8-LED Pmod.

flash_util.py is the start of a utility for writing binary files to flash memory, and reading back flash memory to a file.

### spi

This is the start of a configurable spi controller.

I am still working on how best to do the handshaking.

### wishbone

mitecpu.py is a version of the MiteCPU, converted to access memory via a Wishbone bus. It uses two point-to-point wishbone buses, for code and data.

### uartbridge

blackice_wb.py runs a uart to wishbone bridge (uartbridge.py), to allow [wishbone-tool](https://github.com/litex-hub/wishbone-utils) to read and write FPGA memory, remotely over uart.

Install wishbone-tool and run blackice_wb.py, and you can then run commands such as:

```sh
wishbone-util --serial $DEVICE 0x4000 0x12345678
```

### wishbone_lambda

This version of mitecpu.py is a more extensive wishbone bus example, using components from lambdasoc.


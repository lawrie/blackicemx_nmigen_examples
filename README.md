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

Runmning leds.py counts on the 4 leds. It uses a timer that wraps round into about every second, and sets the 4 leds to the most significant bits of the timer.
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

```
from nmigen import *
from nmigen_boards.blackice_mx import *

class LedGlow(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(4)]
        cnt = Signal(26)
        pwm_input = Signal(4)
        pwm = Signal(5)

        m = Module()

        m.d.sync += [
            cnt.eq(cnt + 1),
            pwm.eq(pwm[:-1] + pwm_input)
        ]

        with m.If(cnt[-1]):
            m.d.sync += pwm_input.eq(cnt[-5:])
        with m.Else():
            m.d.sync += pwm_input.eq(~cnt[-5:])

        for l in led:
            m.d.comb += l.eq(pwm[-1])

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(LedGlow(), do_program=True)
```

### buttons and debouncing

Debounces buttons.

debounce.py counts up on the other 3 leds, when you press button 1, corresponding to the blue led.

### uart

uart.py echoes characters on a uart.

You can do `screen $DEVICE` after uploading the bitstream, and type in characters, or use any other serial terminal program.

This is based on [esden's iCEBreaker example](https://github.com/icebreaker-fpga/icebreaker-nmigen-examples/tree/master/uart) and demonstreate simulation techniques.

### uart_stdio

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

These are audio examples from fpga4fun.com.

They are set up for Digilent Amp2 Pmod in the bottom row of pmod 5 (next to the usb connector), but you can just connect a speaker or earphones to pin 19.

music1.py plays middle C.

music2.py plays 2 tones alternating.

music2a.py plays a siren.

music3.py plays a scale.

music4.py plays a tune.


### ps2_keyboard

This needs a Digilent PS/2 keyboard Pmod connected to the bottom row of pmod5.

When you press a key on the keyboard the scan codes are written in hex to the uart, so run `cat /dev/ttyACM0`.

### mitecpu

This is a [tiny 8-bit cpu](https://github.com/jbush001/MiteCPU) with a python assembler.

The least significant bits of the accumulator are mapped to the cpu.

Assemble programs with assemble.py and run them with mitecpu.py.

### opc

This is an nmigen version of the [opc6](https://revaldinho.github.io/opc/) 16-bit one page CPU.

Assemble programs with opc6asm.py and run them with opc6_sim.py of opc_test.py.

This is just the cpu,m without any connected ram or uart, so it doesn't do much.

### rotary_encoder

This needs a quadrature rotary encoder connected to pins 21 and 22.

Run rotary_encoder.py and see the leds change when yor turn the knob.

### seven_segment

This needs a Digilent 7-segment Pmod in the top row of pmod2 and pmod3 (the side opposite the usb connectors).

Run seven_test.py to run it on the board or seven_seg_sim.py for a nice simulation.

### seven_mixmod

This needs a nystorm 7-segment Mixmod connected on mixmod 1.

Run seven_test.py.

### oled

This needs a 7-pin spi ssd1331 oled display and a Pmod or other means to connect it to pmod5.

Run top_oled_vga.py to put a pattern on the display.

### st7789

This needs a 7-pin spi st7789 display and a Pmod or other means to connect it to pmod5.

The st7789 is a 240x240 color display, as opposed to the 96x64 resolution of the sdd1331, but the prices are similar.

Run st7789_test.py to get a pattern on the display.

### vga

This needs the Digilent VGA Pmod in pmods 2 and 3, opposite the usb connectors.

Run top_vgatest.py to see a pattern on the screen. By default 1024x768@60Hz mode is used.

### sdram

This is an 8-bit dual port SDRAM controller.

Run test_sdram.py to test it.

### sdram16

This is a 16-bit single port SDRAM controller.

Run test_sdram16.py to see the results on the leds: green means passed, red failed.

### ws2812

Test of ws2812b leds (neopixels).

Run ws2812_test.py to test it with a 16-led neopixel ring.

### ping

Test of a 3.3v HC-SR04 ultrasonic (ping) sensor.

Run ping_test.py and press button to take a measurement.

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

### textlcd

This is a start of an example to drive a Hitachi HD44780 2-line text LCD.

### spi

This is the start of a configurable spi controller.

I am still working on how best to do the handshaking.

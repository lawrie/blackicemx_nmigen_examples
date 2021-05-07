# nmigen examples for Blackice MX

## Introduction

These are examples for the Blackice MX ice40 FPGA, written in the python-based nmigen HDL.

You will need to install a version of [nmigen-boards](https://github.com/folknology/nmigen-boards) with Blackice MX support.

To run the blinky example on Linux, plug in your Blackice MX board and do:

```sh
stty -F /dev/ttyACM0 raw
cd blinky
python3 blinky.py
```

You will need nextpnr-ice40 on your path.

The other examples are run in a siimilar way.

You may need to edit icecore.py in nmigen-boards to set the default value for the port parameter in toolchain_program to the value used by your system, for example /dev/ttyACM0.

Some of the examples support simulation as well as running on the board.

The examples have been ported from a variety of sources.

## Examples

### blinky

blinky.py blinks the blue led.

### leds

leds.py count on the 4 leds.

ledglow.py makes all 4 leds glow using PWM.

### uart

uart.py characters on a uart.

e.g. do `screen /dev/ttyACM0`

### audio

These are audio examples from fpga4fun.com.

They are set up for Digilent Amp2 Pmod in the bottom row of pmod 5 (next to the usb connector), but you can just connect a speaker or earphones to pin 19.

music1.py plays middle C.

music2.py plays 2 tones alternating.

music2a.py plays a siren.

music3.py plays a scale.

music4.py plays a tune.

### debounce

Debounces buttons.

debounce.py counts up on the other 3 leds, when you press button 2, corresponding to the blue led.

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

### oled

This needs a 7-pin spi ssd1331 oled display and a Pmod or other means to connect it to pmod5.

Run top_oled_vga.py to put a pattern on the display.


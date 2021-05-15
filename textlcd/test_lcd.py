from nmigen import *
from nmigen_boards.blackice_mx import *
from nmigen.build import *

from textlcd import TextLCD
from math import ceil, log2
from debouncer import Debouncer

lcd_pmod = [
    Resource("lcd", 0,
            Subsignal("rs", Pins("7", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("e", Pins("1", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("data", Pins("3 9 4 10 1 7 2 8", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",0)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        lcd_pins = platform.request("lcd")
        btn = platform.request("button", 0)
        led_g = platform.request("led_g")
        led_r = platform.request("led_r")
        led_y = platform.request("led_y")
        leds8_1 = platform.request("leds8_1");
        leds8 = Cat([i for i in leds8_1.leds])

        m.submodules.textlcd = lcd = TextLCD()

        m.submodules.deb = deb = Debouncer()
        m.d.comb += deb.btn.eq(btn)

        #msg = "\x38\x0f\x01Hello World!\n"
        msg = "\x38\x0f\x01Hello"
        print("msg len:", len(msg))

        COUNT_BITS = ceil(log2(len(msg) + 1))
        print("count bits:", COUNT_BITS)

        count = Signal(COUNT_BITS, reset=0)
        valid = Signal(reset=0)
        e_cycles = Signal(8, reset=0)
        start = Signal(reset=1)

        m.d.comb += [
            lcd_pins.rs.eq(count > 2),
            lcd_pins.e.eq(lcd.e),
            led_g.eq(~lcd.ready),
            led_r.eq(~valid),
            leds8.eq(count),
            led_y.eq(~lcd_pins.rs),
            lcd.valid.eq(valid)
        ]

        with m.If(lcd.e):
            m.d.sync += e_cycles.eq(e_cycles+1)

        with m.If(start):
            m.d.sync += [
                valid.eq(1),
                start.eq(0)
            ]
        with m.Elif(lcd.ready & (count < len(msg)) & deb.btn_down):
            m.d.sync += [
                count.eq(count + 1),
                valid.eq(1)
            ]
        with m.Elif(lcd.ready):
            m.d.sync += valid.eq(0)

        with m.Switch(count):
            for i in range(len(msg)):
                with m.Case(i):
                    m.d.comb += lcd_pins.data.eq(ord(msg[i]))
            with m.Default():
                m.d.comb += lcd_pins.data.eq(0x00)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(lcd_pmod)
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)

from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from ws2812 import WS2812

ws2812_pmod = [
    Resource("ws2812",0,
             Subsignal("data", Pins("7", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        NUM_LEDS = 16

        ws2812 = platform.request("ws2812")
        
        m.submodules.ws2812 = ws = WS2812(NUM_LEDS)

        count     = Signal(20, reset=0)
        color_ind = Signal(2,  reset=0)
        rgb_data  = Signal(24, reset=0x000010)
        led_num   = Signal(5,  reset=0)

        m.d.sync += count.eq(count + 1)

        with m.If(count.all()):
            with m.If(led_num == NUM_LEDS):
                m.d.sync += [
                    led_num.eq(0),
                    color_ind.eq(color_ind + 1)
                ]

                with m.Switch(color_ind):
                    with m.Case(0):
                        m.d.sync += rgb_data.eq(0x100000)
                    with m.Case(1):
                        m.d.sync += rgb_data.eq(0x001000)
                    with m.Case(2):
                        m.d.sync += rgb_data.eq(0x000010)
                    with m.Case(3):
                        m.d.sync += rgb_data.eq(0x101010)

            with m.Else():
                m.d.sync += led_num.eq(led_num + 1)

        m.d.comb += [
            ws2812.data.eq(ws.data),
            ws.rgb_data.eq(rgb_data),
            ws.led_num.eq(led_num),
            ws.write.eq(count.all())
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(ws2812_pmod)
    platform.build(Top(), do_program=True)


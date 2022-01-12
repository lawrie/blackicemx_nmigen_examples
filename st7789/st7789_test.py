from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from  st7789 import *

oled_pmod = [
    Resource("oled", 0,
            Subsignal("oled_clk", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_mosi", Pins("2", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_resn", Pins("9", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_dc", Pins("7", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_csn", Pins("8", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class ST7789Test(Elaboratable):
    def elaborate(self, platform):
        #led = [platform.request("led", i) for i in range(4)]

        # LCD/OLED Pmod
        oled  = platform.request("oled")
        oled_clk  = oled.oled_clk
        oled_mosi = oled.oled_mosi
        oled_dc   = oled.oled_dc
        oled_resn = oled.oled_resn
        oled_csn  = oled.oled_csn

        st7789 = ST7789(reset_delay=100000,reset_period=100000)
        m = Module()
        m.submodules.st7789 = st7789
       
        x = Signal(8)
        y = Signal(8)
        #next_pixel = Signal()
 
        m.d.comb += [
            oled_clk .eq(st7789.spi_clk),
            oled_mosi.eq(st7789.spi_mosi),
            oled_dc  .eq(st7789.spi_dc),
            oled_resn.eq(st7789.spi_resn),
            oled_csn .eq(st7789.spi_csn),
            #oled_csn .eq(1), # For 7-pin version that backlight instead of csn
            #next_pixel.eq(st7789.next_pixel),
            x.eq(st7789.x),
            y.eq(st7789.y),
        ]

        # Draw chequered pattern
        with m.If(x[4] ^ y[4]):
            m.d.comb += st7789.color.eq(x[3:8] << 6)
        with m.Else():
            m.d.comb += st7789.color.eq(y[3:8] << 11)

        #m.d.comb += Cat([i.o for i in led]).eq(st7789.x)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(oled_pmod)

    platform.build(ST7789Test(), do_program=True)

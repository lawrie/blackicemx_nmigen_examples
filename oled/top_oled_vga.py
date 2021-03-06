from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from vga import VGA
from oled_vga import *

oled_pmod = [
    Resource("oled", 0,
            Subsignal("oled_clk", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_mosi", Pins("2", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_resn", Pins("9", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_dc", Pins("7", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_csn", Pins("8", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top_OLED_VGA(Elaboratable):
    def __init__(self):
        # WiFi signaling
        self.io_wifi_en    = Signal()
        self.io_wifi_gpio0 = Signal()

        # On board blinky
        self.o_led = Signal(8)
        self.i_btn = Signal(7)

        # OLED
        self.o_oled_csn  = Signal()
        self.o_oled_clk  = Signal()
        self.o_oled_mosi = Signal()
        self.o_oled_dc   = Signal()
        self.o_oled_resn = Signal()

    def ports(self) -> []:
        return [
            self.o_oled_clk,
            self.o_oled_csn,
            self.o_oled_dc,
            self.o_oled_mosi,
            self.o_oled_resn
        ]

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        m.d.comb += [
            self.io_wifi_en.eq(1),
            self.io_wifi_gpio0.eq(self.i_btn[0])
        ]

        R_counter = Signal(64)
        m.d.sync += R_counter.eq(R_counter + 1)

        # VGA signal generator
        vga_hsync_test = Signal()
        vga_vsync_test = Signal()
        vga_blank_test = Signal()
        vga_rgb_test   = Signal(8)

        m.submodules.vga = vga = DomainRenamer({"pixel":"sync"})(VGA(
            resolution_x      = 96,
            hsync_front_porch = 1800,
            hsync_pulse       = 1,
            hsync_back_porch  = 1800,
            resolution_y      = 64,
            vsync_front_porch = 1,
            vsync_pulse       = 1,
            vsync_back_porch  = 1,
            bits_x            = 12,
            bits_y            = 8
        ))
        m.d.comb += [
            vga.i_clk_en.eq(1),
            vga.i_test_picture.eq(1),
            vga.i_r.eq(0),
            vga.i_g.eq(0),
            vga.i_b.eq(0),
            vga_rgb_test[5:8].eq(vga.o_vga_r[5:8]),
            vga_rgb_test[2:5].eq(vga.o_vga_g[5:8]),
            vga_rgb_test[0:2].eq(vga.o_vga_b[5:8]),
            vga_hsync_test.eq(vga.o_vga_hsync),
            vga_vsync_test.eq(vga.o_vga_vsync),
            vga_blank_test.eq(vga.o_vga_blank),
        ]

        m.submodules.oled = oled = OLED_VGA(color_bits=len(vga_rgb_test))
        m.d.comb += [
            oled.i_clk_en.eq(R_counter[0]),
            oled.i_clk_pixel_ena.eq(1),
            oled.i_blank.eq(vga_blank_test),
            oled.i_hsync.eq(vga_hsync_test),
            oled.i_vsync.eq(vga_vsync_test),
            oled.i_pixel.eq(vga_rgb_test),
            self.o_oled_resn.eq(oled.o_spi_resn),
            self.o_oled_clk .eq(oled.o_spi_clk),
            self.o_oled_csn .eq(oled.o_spi_csn),
            self.o_oled_dc  .eq(oled.o_spi_dc),
            self.o_oled_mosi.eq(oled.o_spi_mosi),
        ]

        m.d.comb += [
            self.o_led[0].eq(self.o_oled_resn),
            self.o_led[1].eq(self.o_oled_csn),
            self.o_led[2].eq(self.o_oled_dc),
            self.o_led[3].eq(self.o_oled_clk),
            self.o_led[4].eq(self.o_oled_mosi),
        ]

        return m

if __name__ == "__main__":
    m = Module()
    m.submodules.top = top = Top_OLED_VGA()

    platform = BlackIceMXPlatform()

    # Add the OLED resource defined above to the platform so we
    # can reference it below.
    platform.add_resources(oled_pmod)

    # LEDs
    leds = [platform.request("led", 0),
            platform.request("led", 1),
            platform.request("led", 2),
            platform.request("led", 3)]

    for i in range(len(leds)):
        m.d.comb += leds[i].eq(top.o_led[i])

    # OLED
    oled = platform.request("oled");
    oled_clk  = oled.oled_clk
    oled_mosi = oled.oled_mosi
    oled_dc   = oled.oled_dc
    oled_resn = oled.oled_resn
    oled_csn  = oled.oled_csn

    m.d.comb += [
        oled_clk .eq(top.o_oled_clk),
        oled_mosi.eq(top.o_oled_mosi),
        oled_dc  .eq(top.o_oled_dc),
        oled_resn.eq(top.o_oled_resn),
        oled_csn .eq(top.o_oled_csn)
    ]

    platform.build(m, do_program=True, nextpnr_opts="--timing-allow-fail")

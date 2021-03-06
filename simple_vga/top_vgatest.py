from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from vga import VGA
from vga_timings import *
from pll import *

vga_pmod = [
    Resource("vga", 0,
             Subsignal("red", Pins("7 8 9 10", dir="o", conn=("pmod", 2)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("green", Pins("7 8 9 10", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("blue", Pins("1 2 3 4", dir="o", conn=("pmod", 2)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("hs", Pins("1", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("vs", Pins("2", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class TopVGATest(Elaboratable):
    def __init__(self,
                 timing: VGATiming, # VGATiming class
                 xadjustf=0, # adjust -3..3 if no picture
                 yadjustf=0): # or to fine-tune f
        # Configuration
        self.timing = timing
        self.x = timing.x
        self.y = timing.y
        self.f = timing.pixel_freq
        self.xadjustf = xadjustf
        self.yadjustf = yadjustf

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        if platform:
            clk_in = platform.request(platform.default_clk, dir='-')[0]

            # Constants
            pixel_f     = self.timing.pixel_freq
            hsync_front_porch = self.timing.h_front_porch
            hsync_pulse_width = self.timing.h_sync_pulse
            hsync_back_porch  = self.timing.h_back_porch
            vsync_front_porch = self.timing.v_front_porch
            vsync_pulse_width = self.timing.v_sync_pulse
            vsync_back_porch  = self.timing.v_back_porch

            # Clock generator.
            m.domains.sync = cd_sync = ClockDomain("sync")
            m.d.comb += ClockSignal().eq(clk_in)

            m.submodules.pll = pll = PLL(freq_in_mhz=int(platform.default_clk_frequency / 1000000), freq_out_mhz=int(pixel_f / 1000000), domain_name="pixel")

            m.domains.pixel = cd_pixel = pll.domain
            m.d.comb += pll.clk_pin.eq(clk_in)

            platform.add_clock_constraint(cd_pixel.clk, pixel_f)

            m.submodules.vga = vga = VGA(
                resolution_x      = self.timing.x,
                hsync_front_porch = hsync_front_porch,
                hsync_pulse       = hsync_pulse_width,
                hsync_back_porch  = hsync_back_porch,
                resolution_y      = self.timing.y,
                vsync_front_porch = vsync_front_porch,
                vsync_pulse       = vsync_pulse_width,
                vsync_back_porch  = vsync_back_porch,
                bits_x            = 16, # Play around with the sizes because sometimes
                bits_y            = 16  # a smaller/larger value will make it pass timing.
            )

            m.d.comb += [
                vga.i_clk_en.eq(1),
                vga.i_test_picture.eq(1),
            ]

            vga_out = platform.request("vga")

            m.d.comb += [
                vga_out.red.eq(vga.o_vga_r[4:]),
                vga_out.green.eq(vga.o_vga_g[4:]),
                vga_out.blue.eq(vga.o_vga_b[4:]),
                vga_out.hs.eq(vga.o_vga_hsync),
                vga_out.vs.eq(vga.o_vga_vsync)
            ]

        return m


if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(vga_pmod)

    m = Module()
    m.submodules.top = top = TopVGATest(timing=vga_timings['1024x768@60Hz'])

    platform.build(m, do_program=True, nextpnr_opts="--timing-allow-fail")


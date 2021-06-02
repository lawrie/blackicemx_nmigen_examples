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

rotary_encoder_pmod = [
    Resource("rotary_encoder", 0,
            Subsignal("quadrature", Pins("7", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("in_phase", Pins("8", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Pong(Elaboratable):
    def __init__(self,
                 timing: VGATiming, # VGATiming class
                 xadjustf=0, # adjust -3..3 if no picture
                 yadjustf=0): # or to fine-tune f
        self.o_led = Signal(8)
        self.o_gpdi_dp = Signal(4)
        self.o_user_programn = Signal()
        self.o_wifi_gpio0 = Signal()
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
            encoder_pins = platform.request("rotary_encoder")
            quada = encoder_pins.quadrature
            quadb = encoder_pins.in_phase

            # Constants
            pixel_f     = self.timing.pixel_freq
            hsync_front_porch = self.timing.h_front_porch
            hsync_pulse_width = self.timing.h_sync_pulse
            hsync_back_porch  = self.timing.h_back_porch
            vsync_front_porch = self.timing.v_front_porch
            vsync_pulse_width = self.timing.v_sync_pulse
            vsync_back_porch  = self.timing.v_back_porch

            m.submodules.pll = pll = PLL(freq_in_mhz=int(platform.default_clk_frequency / 1000000), freq_out_mhz=int(pixel_f / 1000000), domain_name="pixel")

            m.domains.pixel = cd_pixel = pll.domain
            m.d.comb += pll.clk_pin.eq(ClockSignal())

            # VGA signal generator.
            vga_r = Signal(8)
            vga_g = Signal(8)
            vga_b = Signal(8)
            vga_hsync = Signal()
            vga_vsync = Signal()
            vga_blank = Signal()

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

            border  = Signal()
            paddle  = Signal()
            ball    = Signal()
            bouncer = Signal()
            x       = Signal(10)
            y       = Signal(9)
            bx      = Signal(10)
            by      = Signal(9)
            pp      = Signal(10)
            b_d_x   = Signal()
            b_d_y   = Signal()
            rc      = Signal()
            cx1     = Signal()
            cx2     = Signal()
            cy1     = Signal()
            cy2     = Signal()
            r_quada = Signal(3)
            r_quadb = Signal(3)

            m.d.pixel += [
                r_quada.eq(Cat(quada, r_quada[:2])),
                r_quadb.eq(Cat(quadb, r_quadb[:2]))
            ]

            with m.If(r_quada[2] ^ r_quada[1] ^ r_quadb[2] ^ r_quadb[1]):
                with m.If(r_quada[2] ^ r_quadb[1]):
                    with m.If(~pp.all()):
                        m.d.pixel += pp.eq(pp + 1)
                with m.Else():
                    with m.If(pp.any()):
                        m.d.pixel += pp.eq(pp - 1)

            with m.If(rc):
                m.d.pixel += [
                    cx1.eq(0),
                    cx2.eq(0),
                    cy1.eq(0),
                    cy2.eq(0)
                ]
                with m.If(~(cx1 & cx2)):
                    m.d.pixel += bx.eq(bx + Mux(b_d_x, -1, 1))
                    with m.If(cx2):
                        m.d.pixel += b_d_x.eq(1)
                    with m.Elif(cx1):
                        m.d.pixel += b_d_x.eq(0)
                with m.If(~(cy1 & cy2)):
                    m.d.pixel += by.eq(by + Mux(b_d_y, -1, 1))
                    with m.If(cy2):
                        m.d.pixel += b_d_y.eq(1)
                    with m.Elif(cy1):
                        m.d.pixel += b_d_y.eq(0)
            with m.Elif(bouncer):
                with m.If((x == bx) & (y == by + 8)):
                    m.d.pixel += cx1.eq(1)
                with m.If((x == bx + 16) & (y == by + 8)):
                    m.d.pixel += cx2.eq(1)
                with m.If((x == bx + 8) & (y == by)):
                    m.d.pixel += cy1.eq(1)
                with m.If((x == bx + 8) & (y == by + 16)):
                    m.d.pixel += cy2.eq(1)

            m.d.comb += [
                x.eq(vga.o_beam_x),
                y.eq(vga.o_beam_y),
                rc.eq((x == 0) & (y == 500)),
                border.eq((x[3:] == 0) | (x[3:] == 79) | (y[3:] == 0) | (y[3:] == 59)), 
                paddle.eq((x >= pp + 8) & (x <= pp + 120) & (y[4:] == 27)),
                bouncer.eq(border | paddle),
                ball.eq((x >= bx) & (x < (bx + 16)) & (y >= by) & (y < (by + 16))),
                vga.i_clk_en.eq(1),
                vga.i_test_picture.eq(0),
                vga.i_r.eq(Mux(bouncer | ball | (vga.o_beam_x[3] ^ vga.o_beam_y[3]), 0xff, 0)),
                vga.i_b.eq(Mux(bouncer | ball, 0xff, 0)),
                vga.i_g.eq(Mux(bouncer | ball, 0xff, 0)),
                vga_r.eq(vga.o_vga_r),
                vga_g.eq(vga.o_vga_g),
                vga_b.eq(vga.o_vga_b),
                vga_hsync.eq(vga.o_vga_hsync),
                vga_vsync.eq(vga.o_vga_vsync),
                vga_blank.eq(vga.o_vga_blank),
            ]

            vga_out = platform.request("vga")

            m.d.comb += [
                vga_out.red.eq(vga_r[4:]),
                vga_out.green.eq(vga_g[4:]),
                vga_out.blue.eq(vga_b[4:]),
                vga_out.hs.eq(vga_hsync),
                vga_out.vs.eq(vga_vsync)
            ]

        return m


if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(vga_pmod)
    platform.add_resources(rotary_encoder_pmod)

    m = Module()
    m.submodules.top = top = Pong(timing=vga_timings['640x480@60Hz'])

    platform.build(m, do_program=True, nextpnr_opts="--timing-allow-fail")


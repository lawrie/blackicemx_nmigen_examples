from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from camread import *
from camconfig import *
from image_stream import *
from debouncer import *

from vga import VGA
from vga_timings import *
from pll import PLL
from sdram_controller16 import sdram_controller
from osd import OSD

# Digilent 4-bit per color VGA Pmod
vga_pmod = [
    Resource("vga", 0,
             Subsignal("red", Pins("7 8 9 10", dir="o", conn=("pmod", 2)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("green", Pins("7 8 9 10", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("blue", Pins("1 2 3 4", dir="o", conn=("pmod", 2)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("hs", Pins("1", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("vs", Pins("2", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# iCEBreaker Pmod with 3 buttons and 5 leds
btn_led_pmod = [
    Resource("btn_led", 0,
             Subsignal("led_g", Pins("7 8 9 2", dir="o", conn=("pmod", 5)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("led_r", Pins("1", dir="o", conn=("pmod", 5)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("btn", Pins("3 10 4", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# OV7670 camera Pmod
ov7670_pmod = [
    Resource("ov7670", 0,
             Subsignal("cam_data", Pins("2 17 3 18 4 19 10 25", dir="i", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("cam_SIOD", Pins("13", dir="o", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("cam_SIOC", Pins("28", dir="o", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("cam_HREF", Pins("12", dir="i", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("cam_VSYNC", Pins("27", dir="i", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("cam_PCLK", Pins("26", dir="i", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("cam_XCLK", Pins("11", dir="o", conn=("mixmod", 0)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# Image processing from OV7670 camera using SDRAM for frame buffer and VGA output
class CamTest(Elaboratable):
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

    def elaborate(self, platform):
        # Constants
        pixel_f     = self.timing.pixel_freq
        hsync_front_porch = self.timing.h_front_porch
        hsync_pulse_width = self.timing.h_sync_pulse
        hsync_back_porch  = self.timing.h_back_porch
        vsync_front_porch = self.timing.v_front_porch
        vsync_pulse_width = self.timing.v_sync_pulse
        vsync_back_porch  = self.timing.v_back_porch

        m = Module()
       
        # Get pins
        led = [platform.request("led", i) for i in range(2,4)]
        leds = Cat([i.o for i in led])
        ov7670 = platform.request("ov7670")
        btn1 = platform.request("button", 0)
        btn2 = platform.request("button", 1)
        btn_led = platform.request("btn_led", 0)
        up = btn_led.btn[2]
        down = btn_led.btn[0]
        sel = btn_led.btn[1]
        ledfeat = Cat([i for i in btn_led.led_g])
        led_r = btn_led.led_r
        clk_in = platform.request(platform.default_clk, dir='-')[0]

        # Clock generator.
        # PLL - 64MHz for sdram
        m.submodules.pll = pll = PLL(freq_in_mhz=25, freq_out_mhz=100, domain_name="sdram")

        m.domains.sdram = cd_sdram = pll.domain
        m.d.comb += pll.clk_pin.eq(clk_in)

        # Divide clock by 4
        div = Signal(3)
        m.d.sdram += div.eq(div+1)

        # Power-on reset
        reset = Signal(13, reset=0)
        with m.If(~reset.all()):
            m.d.sdram += reset.eq(reset+1)

        # Make sync domain 25MHz
        m.domains.sync = cd_sync = ClockDomain("sync")
        m.d.comb += ResetSignal().eq(~reset.all())
        m.d.comb += ClockSignal().eq(div[1])

        # Add the SDRAM controller
        m.submodules.mem = mem = sdram_controller()

        m.domains.pixel = cd_pixel = ClockDomain("pixel")
        m.d.comb += ClockSignal("pixel").eq(div[1])

        lb = Memory(width=16, depth=320)
        m.submodules.r = r = lb.read_port()
        m.submodules.w = w = lb.write_port()

        # Add CamRead submodule
        camread = CamRead()
        m.submodules.camread = camread

        # Camera config
        camconfig = CamConfig()
        m.submodules.camconfig = camconfig

        # Configure and read the camera
        m.d.comb += [
            ov7670.cam_XCLK.eq(ClockSignal()),
            ov7670.cam_SIOC.eq(camconfig.sioc),
            ov7670.cam_SIOD.eq(camconfig.siod),
            camconfig.start.eq(btn1),
            camread.p_data.eq(Cat([ov7670.cam_data[i] for i in range(8)])),
            camread.href.eq(ov7670.cam_HREF),
            camread.vsync.eq(ov7670.cam_VSYNC),
            camread.p_clock.eq(ov7670.cam_PCLK)
        ]

        # Buttons and valiues for brightness etc.
        debup = Debouncer()
        m.submodules.debup = debup

        osd_on = Signal(reset=1)
        osd_val = Signal(4, reset=0)

        val = Signal(signed(7), reset=0)
        brightness = Signal(signed(7), reset=0)
        redness = Signal(signed(7), reset=0)
        greenness = Signal(signed(7), reset=0)
        blueness = Signal(signed(7), reset=0)

        debdown = Debouncer()
        m.submodules.debdown = debdown

        debosd = Debouncer()
        m.submodules.debosd = debosd

        debsel = Debouncer()
        m.submodules.debsel = debsel

        xflip = Signal(reset=0)
        yflip = Signal(reset=1)
        mono = Signal(reset=0)
        invert = Signal(reset=0)
        gamma = Signal(reset=0)
        border = Signal(reset=0)
        filt = Signal(reset=0)
        edge = Signal(reset=0)

        osd_sel = Signal(reset=0)

        m.d.comb += [
            debup.btn.eq(up),
            debdown.btn.eq(down),
            debosd.btn.eq(btn2),
            debsel.btn.eq(sel),
            ledfeat.eq(Cat([mono, xflip, yflip, border])),
            led_r.eq(edge)
        ]

        # OSD
        with m.If(debup.btn_down):
            with m.If(osd_on & ~osd_sel):
                m.d.sync += osd_val.eq(Mux(osd_val == 11, 0, osd_val+1))
            with m.Elif(osd_sel): 
                with m.Switch(osd_val):
                    with m.Case(0): # brightness
                        m.d.sync += brightness.eq(brightness+1)
                    with m.Case(1): # redness
                        m.d.sync += redness.eq(redness+1)
                    with m.Case(2): # greenness
                        m.d.sync += greenness.eq(greenness+1)
                    with m.Case(3): # blueness
                        m.d.sync += blueness.eq(blueness+1)
                    with m.Case(4): # mono
                        m.d.sync += mono.eq(1)
                    with m.Case(5): # x flip
                        m.d.sync += xflip.eq(1)
                    with m.Case(6): # y flip
                        m.d.sync += yflip.eq(1)
                    with m.Case(7): # border
                        m.d.sync += border.eq(1)
                    with m.Case(8): # edge detection
                        m.d.sync += edge.eq(1)
                    with m.Case(9): # invert
                        m.d.sync += invert.eq(1)
                    with m.Case(10): # gamma
                        m.d.sync += gamma.eq(1)

        with m.If(debdown.btn_down):
            with m.If(osd_on & ~osd_sel):
                m.d.sync += osd_val.eq(Mux(osd_val == 0, 11, osd_val-1))
            with m.Elif(osd_sel): 
                with m.Switch(osd_val):
                    with m.Case(0): # brightness
                        m.d.sync += brightness.eq(brightness-1)
                    with m.Case(1): # redness
                        m.d.sync += redness.eq(redness-1)
                    with m.Case(2): # greenness
                        m.d.sync += greenness.eq(greenness-1)
                    with m.Case(3): # blueness
                        m.d.sync += blueness.eq(blueness-1)
                    with m.Case(4): # mono
                        m.d.sync += mono.eq(0)
                    with m.Case(5): # x flip
                        m.d.sync += xflip.eq(0)
                    with m.Case(6): # y flip
                        m.d.sync += yflip.eq(0)
                    with m.Case(7): # border
                        m.d.sync += border.eq(0)
                    with m.Case(8): # edge detection
                        m.d.sync += edge.eq(0)
                    with m.Case(9): # invert
                        m.d.sync += invert.eq(0)
                    with m.Case(10): # gamma
                        m.d.sync += gamma.eq(0)

        # Image stream
        max_r = Signal(5)
        max_g = Signal(6)
        max_b = Signal(5)

        ims = ImageStream(res_x=320, res_y=240)
        m.submodules.image_stream = ims

        m.d.comb += [
            ims.valid.eq(camread.pixel_valid),
            ims.i_x.eq(camread.row[1:]),
            ims.i_y.eq(camread.col[1:]),
            ims.i_r.eq(camread.pixel_data[11:]),
            ims.i_g.eq(camread.pixel_data[5:11]),
            ims.i_b.eq(camread.pixel_data[0:5]),
            ims.edge.eq(edge),
            ims.invert.eq(invert),
            ims.border.eq(border),
            ims.gamma.eq(gamma),
            ims.filter.eq(filt),
            ims.mono.eq(mono),
            ims.x_flip.eq(xflip),
            ims.y_flip.eq(yflip),
            ims.val.eq(val),
            ims.redness.eq(redness),
            ims.greenness.eq(greenness),
            ims.blueness.eq(blueness),
            ims.brightness.eq(brightness)
        ]

        # Frame-level statistics
        with m.If(ims.i_r > max_r):
            m.d.sync += max_r.eq(ims.i_r) 
        with m.If(ims.i_g > max_g):
            m.d.sync += max_g.eq(ims.i_g) 
        with m.If(ims.i_b > max_b):
            m.d.sync += max_b.eq(ims.i_b) 

        with m.If(camread.frame_done):
            m.d.sync += [
                max_r.eq(0),
                max_g.eq(0),
                max_b.eq(0),
                leds.eq(leds+1)
            ]

        # VGA signal generator.
        vga_r = Signal(8)
        vga_g = Signal(8)
        vga_b = Signal(8)
        vga_hsync = Signal()
        vga_vsync = Signal()
        vga_blank = Signal()

        psum = Signal(8)

        # Add VGA generator
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

        # Write to SDRAM
        raddr = Signal(20)    # SDRAM read address
        waddr = Signal(20)    # SDRAM write address
        read_pixel = Signal() # Set when pixel is being read from SDRAM
        x = Signal(10)        # VGA x co-ordinate
        x1 = Signal(10)       # VGA x + 1
        x2 = Signal(10)       # VGA X + 2
        xm2 = Signal(10)      # VGA x - 1
        y = Signal(10)        # VGA y

        m.d.comb += [
            x.eq(vga.o_beam_x),
            x1.eq(x + 1),
            x2.eq(x + 2),
            xm2.eq(x - 2),
            y.eq(vga.o_beam_y),
            raddr.eq((y[1:] * 320) + x2[1:]), # 2 cycles to read
            waddr.eq((ims.o_y * 320) + ims.o_x),
            read_pixel.eq(~vga_blank & x[1] & ~y[0]),
            mem.init.eq(~pll.locked), # Use pll not locked as signal to initialise SDRAM
            mem.sync.eq(~div[2]),      # Sync with 25MHz clock
            mem.address.eq(Mux(read_pixel, raddr, waddr)),
            mem.data_in.eq(Cat(ims.o_b, ims.o_g, ims.o_r)),
            mem.req_read.eq(~div[2] & read_pixel), # Always read when pixel requested
            mem.req_write.eq(~div[2] & ~read_pixel & ims.ready) # Don't write when reading
        ]

        # Duplicate lines in line buffer
        m.d.comb += [
            w.addr.eq(xm2[1:]),         # 0 - 319, SDRAM data is 2 cycles late
            r.addr.eq(x1[1:]),          # 1 cycle to read
            w.data.eq(mem.data_out),    # Write data just read from SDRAM
            w.en.eq(~vga_blank & ~y[0]) # Write if first of 2 vertical lines
        ]

        # Generate VGA signals
        m.d.comb += [
            vga.i_clk_en.eq(1),
            vga.i_test_picture.eq(0),
            vga.i_r.eq(Cat(Const(0, unsigned(3)), Mux(y[0], r.data[11:], mem.data_out[11:]))), 
            vga.i_g.eq(Cat(Const(0, unsigned(2)), Mux(y[0], r.data[5:11], mem.data_out[5:11]))), 
            vga.i_b.eq(Cat(Const(0, unsigned(3)), Mux(y[0], r.data[0:5], mem.data_out[0:5]))), 
            vga_r.eq(vga.o_vga_r),
            vga_g.eq(vga.o_vga_g),
            vga_b.eq(vga.o_vga_b),
            vga_hsync.eq(vga.o_vga_hsync),
            vga_vsync.eq(vga.o_vga_vsync),
            vga_blank.eq(vga.o_vga_blank),
        ]

        # Drive VGA pins
        vga_out = platform.request("vga")

        # OSD
        m.submodules.osd = osd = OSD()

        with m.If(debosd.btn_down):
            m.d.sync += [
                osd_on.eq(~osd_on),
                osd_sel.eq(0)
            ]
            
        m.d.comb += [
            osd.x.eq(x),
            osd.y.eq(y),
            osd.i_r.eq(vga.o_vga_r[4:]),
            osd.i_g.eq(vga.o_vga_g[4:]),
            osd.i_b.eq(vga.o_vga_b[4:]),
            osd.on.eq(osd_on),
            osd.osd_val.eq(osd_val),
            osd.sel.eq(osd_sel)
        ]


        m.d.comb += [
            vga_out.red.eq(osd.o_r),
            vga_out.green.eq(osd.o_g),
            vga_out.blue.eq(osd.o_b),
            vga_out.hs.eq(vga_hsync),
            vga_out.vs.eq(vga_vsync)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()

    m = Module()
    m.submodules.top = top = CamTest(timing=vga_timings['640x480@60Hz'])

    platform.add_resources(ov7670_pmod)
    platform.add_resources(vga_pmod)
    platform.add_resources(btn_led_pmod)

    platform.build(m, do_program=True, nextpnr_opts="")


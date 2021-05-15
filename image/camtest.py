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

vga_pmod = [
    Resource("vga", 0,
             Subsignal("red", Pins("7 8 9 10", dir="o", conn=("pmod", 2)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("green", Pins("7 8 9 10", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("blue", Pins("1 2 3 4", dir="o", conn=("pmod", 2)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("hs", Pins("1", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("vs", Pins("2", dir="o", conn=("pmod", 3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# The OLED pins are not defined in the ULX3S platform in nmigen_boards.
oled_pmod = [
    Resource("oled", 0,
            Subsignal("oled_clk", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_mosi", Pins("2", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_resn", Pins("9", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_dc", Pins("7", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_csn", Pins("8", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

btn_led_pmod = [
    Resource("btn_led", 0,
             Subsignal("led_g", Pins("7 8 9 2", dir="o", conn=("pmod", 5)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("led_r", Pins("1", dir="o", conn=("pmod", 5)), Attrs(IO_STANDARD="SB_LVCMOS")),
             Subsignal("btn", Pins("3 10 4", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

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

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

leds8_2_pmod = [
    Resource("leds8_2", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

switch_pmod = [
    Resource("sw8", 0,
             Subsignal("sw", Pins("7 8 1 2 3 4", dir="i", conn=("pmod", 4)), Attrs(IO_STANDARD="LVCMOS3")))
]

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
        
        # Clock generator.
        m.domains.pixel = cd_pixel = ClockDomain("pixel")
        m.d.comb += ClockSignal("pixel").eq(ClockSignal())

        platform.add_clock_constraint(cd_pixel.clk, pixel_f)

        led = [platform.request("led", i) for i in range(2,4)]
        leds = Cat([i.o for i in led])
        ov7670 = platform.request("ov7670")
        btn1 = platform.request("button", 0)
        btn2 = platform.request("button", 1)
        btn_led = platform.request("btn_led", 0)
        up = btn_led.btn[2]
        down = btn_led.btn[0]
        feat = btn_led.btn[1]
        ledfeat = Cat([i for i in btn_led.led_g])

        #sw8 = platform.request("sw8")
        sw0 = Signal()
        sw1 = Signal()
        sw2 = Signal()
        sw3 = Signal()

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

        # Frame buffer
        buffer = Memory(width=16, depth=80 * 60)
        m.submodules.r = r = buffer.read_port()
        m.submodules.w = w = buffer.write_port()

        # Buttons and val
        debup = Debouncer()
        m.submodules.debup = debup

        val = Signal(signed(6))
        up_down = Signal()

        debdown = Debouncer()
        m.submodules.debdown = debdown

        debres = Debouncer()
        m.submodules.debres = debres

        debfeat = Debouncer()
        m.submodules.debfeat = debfeat

        m.d.comb += [
            debup.btn.eq(up),
            debdown.btn.eq(down),
            debres.btn.eq(btn2),
            debfeat.btn.eq(feat)
        ]

        with m.If(debup.btn_down):
            m.d.sync += val.eq(val+1)

        with m.If(debdown.btn_down):
            m.d.sync += val.eq(val-1)

        with m.If(debres.btn_down):
            m.d.sync += val.eq(0)

        feature = Signal(4)

        with m.If(debfeat.btn_down):
            m.d.sync += feature.eq(feature+1)

        m.d.comb += ledfeat.eq(feature)

        # Image stream
        max_r = Signal(5)
        max_g = Signal(6)
        max_b = Signal(5)

        ims = ImageStream(res_x=80, res_y=60)
        m.submodules.image_stream = ims

        m.d.comb += [
            ims.valid.eq(camread.pixel_valid),
            ims.i_x.eq(camread.row[3:]),
            ims.i_y.eq(camread.col[3:]),
            ims.i_r.eq(camread.pixel_data[11:]),
            ims.i_g.eq(camread.pixel_data[5:11]),
            ims.i_b.eq(camread.pixel_data[0:5]),
            #ims.edge.eq(sw8.sw[0]),
            ims.edge.eq(0),
            #ims.red.eq(sw8.sw[1]),
            ims.red.eq(0),
            #ims.green.eq(sw8.sw[2]),
            ims.green.eq(0),
            #ims.blue.eq(sw8.sw[3]),
            ims.blue.eq(0),
            #ims.invert.eq(0),
            ims.invert.eq(0),
            ims.border.eq(0),
            #ims.gamma.eq(sw8.sw[6]),
            ims.gamma.eq(0),
            #ims.filter.eq(sw8.sw[7]),
            ims.filter.eq(0),
            ims.mono.eq(feature[0]),
            ims.bright.eq(1),
            ims.x_flip.eq(feature[1]),
            ims.y_flip.eq(feature[2]),
            ims.val.eq(val)
        ]

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

        # Connect frame buffer
        m.d.comb += [
            w.en.eq(ims.ready),
            w.addr.eq(ims.o_y * 80 + ims.o_x),
            w.data.eq(Cat(ims.o_b, ims.o_g, ims.o_r)),
            r.addr.eq(vga.o_beam_y[3:] * 80 + vga.o_beam_x[3:])
        ]

        # Generate VGA signals
        m.d.comb += [
            vga.i_clk_en.eq(1),
            vga.i_test_picture.eq(0),
            vga.i_r.eq(Cat(Const(0, unsigned(3)), r.data[11:16])), 
            vga.i_g.eq(Cat(Const(0, unsigned(2)), r.data[5:11])), 
            vga.i_b.eq(Cat(Const(0, unsigned(3)), r.data[0:5])), 
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

    m = Module()
    m.submodules.top = top = CamTest(timing=vga_timings['640x480@60Hz'])

    platform.add_resources(ov7670_pmod)
    platform.add_resources(switch_pmod)
    platform.add_resources(vga_pmod)
    platform.add_resources(btn_led_pmod)

    platform.build(m, do_program=True)


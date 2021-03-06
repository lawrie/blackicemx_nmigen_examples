from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from camread import *
from st7789 import *
from camconfig import *
from pll import PLL

from sdram_controller16 import sdram_controller

# The OLED pins are not defined in the ULX3S platform in nmigen_boards.
oled_pmod = [
    Resource("oled", 0,
            Subsignal("oled_clk", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_mosi", Pins("2", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_resn", Pins("9", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_dc", Pins("7", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("oled_csn", Pins("8", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
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

class CamTest(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(2,4)]
        leds = Cat([i.o for i in led])
        ov7670 = platform.request("ov7670")
        btn1 = platform.request("button", 0)
        btn2 = platform.request("button", 1)
        clk_in = platform.request(platform.default_clk, dir='-')[0]
        leds8_1 = platform.request("leds8_1")
        leds8_2 = platform.request("leds8_2")
        led16 = [i for i in leds8_1] + [i for i in leds8_2]
        leds16 = Cat([i for i in led16])

        m = Module()
        
        # Clock generation
        # PLL - 64MHz for sdram
        m.submodules.pll = pll = PLL(freq_in_mhz=25, freq_out_mhz=100, domain_name="sdram")

        m.domains.sdram = cd_sdram = pll.domain
        m.d.comb += pll.clk_pin.eq(clk_in)

        # Divide clock by 4
        div = Signal(3)
        m.d.sdram += div.eq(div+1)

        # Power-on reset
        reset = Signal(16, reset=0)
        with m.If(~reset.all()):
            m.d.sdram += reset.eq(reset+1)

        # Make sync domain 25MHz
        m.domains.sync = cd_sync = ClockDomain("sync")
        m.d.comb += ResetSignal().eq(~reset.all() | btn2)
        m.d.comb += ClockSignal().eq(div[1])

        # Add the SDRAM controller
        m.submodules.mem = mem = sdram_controller()

        # Add CamRead submodule
        camread = CamRead()
        m.submodules.camread = camread

        # Add ST7789 submodule
        st7789 = ST7789(150000)
        m.submodules.st7789 = st7789

        # OLED
        oled  = platform.request("oled")
        oled_clk  = oled.oled_clk
        oled_mosi = oled.oled_mosi
        oled_dc   = oled.oled_dc
        oled_resn = oled.oled_resn
        oled_csn  = oled.oled_csn

        # Camera config
        camconfig = CamConfig()
        m.submodules.camconfig = camconfig

        m.d.comb += [
            oled_clk .eq(st7789.spi_clk),
            oled_mosi.eq(st7789.spi_mosi),
            oled_dc  .eq(st7789.spi_dc),
            oled_resn.eq(st7789.spi_resn),
            oled_csn .eq(1),
            ov7670.cam_XCLK.eq(div[1]),
            camread.p_data.eq(Cat([ov7670.cam_data[i] for i in range(8)])),
            camread.href.eq(ov7670.cam_HREF),
            camread.vsync.eq(ov7670.cam_VSYNC),
            camread.p_clock.eq(ov7670.cam_PCLK),
            st7789.color.eq(mem.data_out),
            camconfig.start.eq(btn1),
            ov7670.cam_SIOC.eq(camconfig.sioc),
            ov7670.cam_SIOD.eq(camconfig.siod),
        ]

        pixel_valid2 = Signal()
        pixel_valid = Signal()

        m.d. sync += [
            pixel_valid2.eq(camread.pixel_valid)
        ]

        m.d.comb += pixel_valid.eq(camread.pixel_valid | pixel_valid2)

        raddr = Signal(20)
        waddr = Signal(20)
        sync  = Signal()

        # Write to SDRAM
        m.d.comb += [
            sync.eq(~div[2]),
            raddr.eq(((239 - st7789.x) * 320) + st7789.y),
            waddr.eq((camread.row[1:] * 320) + camread.col[1:]),
            mem.init.eq(~pll.locked), # Use pll not locked as signal to initialise SDRAM
            mem.sync.eq(sync),      # Sync with 25MHz clock
            mem.address.eq(Mux(st7789.next_pixel, raddr, waddr)),
            mem.data_in.eq(camread.pixel_data),
            mem.req_read.eq(sync & st7789.next_pixel), # Always read when pixel requested
            mem.req_write.eq(sync & ~st7789.next_pixel & pixel_valid), # Delay write one cycle if needed
            leds16.eq(mem.data_out)
        ]

        with m.If(camread.frame_done):
            m.d.sync += leds.eq(leds + 1)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(ov7670_pmod)    
    platform.add_resources(oled_pmod)
    platform.add_resources(leds8_1_pmod)
    platform.add_resources(leds8_2_pmod)
    platform.build(CamTest(), do_program=True)


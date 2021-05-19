from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from nmigen.lib.fifo import SyncFIFOBuffered

from camread import *
from st7789 import *
from camconfig import *
from pll import PLL

from sdram_controller16 import sdram_controller

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
        
        # FIFO for camera input, can be just a few pixels with LCD screen
        m.submodules.fifo = fifo = SyncFIFOBuffered(width=16,depth=3)

        # SDRAM read and write addresses
        raddr = Signal(20)
        waddr = Signal(20, reset=0)

        # Co-ordinates in SDRAM buffer
        x = Signal(8, reset=0)
        y = Signal(8, reset=0)

        # FIFO and SDRAM signals
        start         = Signal(reset=1)
        fifo_wen      = Signal()
        fifo_ren      = Signal()
        mem_ren       = Signal()
        mem_wen       = Signal()
        r_mem_wen     = Signal()
        sdram_sync    = Signal()
        r_next_pixel  = Signal()
        r2_next_pixel = Signal()

        m.d.sync += [
            mem_wen.eq(fifo_ren),               # Write to memory the cycle after reading fifo
            r_mem_wen.eq(mem_wen),              # Cycle after is when we update SDRAM buffer co-ordinates
            r_next_pixel.eq(st7789.next_pixel), # Cycle after requesting next pixel
            r2_next_pixel.eq(r_next_pixel)      # Cycle after that is when we do the read of SDRAM
        ]

        # Sync SDRAM buffer co-ordinate with camera frame
        with m.If(start & camread.frame_done):
            m.d.sync += [
                x.eq(0),
                y.eq(0),
                start.eq(0)
            ]

        # Update co-ordinates after writing to SDRAM
        with m.If(r_mem_wen):
            with m.If(x == (240 - 1)):
                m.d.sync += x.eq(0)

                with m.If(y == (240 - 1)):
                    m.d.sync += y.eq(0)
                with m.Else():
                    m.d.sync += y.eq(y+1)
            with m.Else():
                m.d.sync += x.eq(x+1)

        # Check the FIFO never gets full
        with m.If(~fifo.w_rdy):
            m.d.sync += led[0].eq(1)

        # Read from FIFO, and write to SDRAM
        m.d.comb += [
            # Sync SDRAM clock to every other cycle of sync domain
            # Note that st7789 driver takes 32 cycles per pixel and stays in sync
            sdram_sync.eq(~div[2]),
            mem.sync.eq(sdram_sync),
            mem.init.eq(~pll.locked),   # Use pll not locked as signal to initialise SDRAM
            # Select 240 x 240 frame
            fifo_wen.eq(camread.pixel_valid & camread.col[0] & camread.row[0] & (camread.row < 480)),
            # Avoid fifo read when next pixel is requested
            fifo_ren.eq(~sdram_sync & fifo.r_rdy & ~r_next_pixel),
            # Do read rather than write when next pixel is requested (2 cycles later)
            mem_ren.eq(sdram_sync & r2_next_pixel),
            mem.req_read.eq(mem_ren),   # Always read when pixel requested
            mem.data_in.eq(fifo.r_data),
            mem.req_write.eq(mem_wen), 
            # Write camera pixels to the FIFO
            fifo.w_data.eq(camread.pixel_data),
            # Reduce to 240 x 240
            fifo.w_en.eq(fifo_wen),
            # Read from the FIFO when ready to write to SDRAM
            fifo.r_en.eq(fifo_ren),
            # Set the SDRAM read and write addresses
            raddr.eq((st7789.y * 240) + st7789.x),
            waddr.eq((y * 240) + (239 - x)),
            mem.address.eq(Mux(mem_ren, raddr, waddr)),
            leds16.eq(mem.data_out)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(ov7670_pmod)    
    platform.add_resources(oled_pmod)
    platform.add_resources(leds8_1_pmod)
    platform.add_resources(leds8_2_pmod)
    platform.build(CamTest(), do_program=True)


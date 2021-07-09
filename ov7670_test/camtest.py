from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from nmigen.lib.fifo import SyncFIFOBuffered

from camread import *
from st7789 import *
from camconfig import *

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
        led = [platform.request("led", i) for i in range(1,4)]
        leds = Cat([i.o for i in led])
        ov7670 = platform.request("ov7670")
        btn1 = platform.request("button", 0)
        leds8_1 = platform.request("leds8_1")
        leds8_2 = platform.request("leds8_2")
        led16 =  [i for i in leds8_1] + [i for i in leds8_2]
        leds16 = Cat([i for i in led16])

        m = Module()
        
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

        # Frame buffer
        buffer = Memory(width=16, depth=80 * 60)
        m.submodules.r = r = buffer.read_port()
        m.submodules.w = w = buffer.write_port()
        
        # Camera config
        camconfig = CamConfig()
        m.submodules.camconfig = camconfig

        m.d.comb += [
            oled_clk .eq(st7789.spi_clk),
            oled_mosi.eq(st7789.spi_mosi),
            oled_dc  .eq(st7789.spi_dc),
            oled_resn.eq(st7789.spi_resn),
            oled_csn .eq(1),
            ov7670.cam_XCLK.eq(ClockSignal()),
            camread.p_data.eq(Cat([ov7670.cam_data[i] for i in range(8)])),
            camread.href.eq(ov7670.cam_HREF),
            camread.vsync.eq(ov7670.cam_VSYNC),
            camread.p_clock.eq(ov7670.cam_PCLK),
            #w.en.eq(camread.pixel_valid),
            #w.addr.eq(((camread.row[3:] - 0) * 80) + camread.col[3:]),
            #w.data.eq(camread.pixel_data),
            r.addr.eq(((59 - st7789.x[2:]) * 80) + st7789.y[2:]),
            st7789.color.eq(r.data),
            camconfig.start.eq(btn1),
            ov7670.cam_SIOC.eq(camconfig.sioc),
            ov7670.cam_SIOD.eq(camconfig.siod),
        ]

        m.submodules.fifo = fifo = SyncFIFOBuffered(width=16,depth=1024)

        waddr = Signal(13)
        x = Signal(10, reset=0)
        y = Signal(9, reset=0)
        start = Signal(reset=1)

        with m.If(start & camread.frame_done):
            m.d.sync += [
                x.eq(0),
                y.eq(0),
                #waddr.eq(dd0),
                start.eq(0)
            ]

        with m.If(fifo.r_rdy):
            #with m.If((y[:3] == 7) & (x[:3] == 7)):
            #    m.d.sync += waddr.eq(Mux(waddr == (80 * 60) - 1, 0, waddr+1))

            with m.If(x == 640 -1):
                m.d.sync += x.eq(0)

                with m.If(y == 480 -1):
                    m.d.sync += y.eq(0)
                with m.Else():
                    m.d.sync += y.eq(y+1)
            with m.Else():
                m.d.sync += x.eq(x+1)

        m.d.comb += [
            waddr.eq((y[3:] * 80) + x[3:]),
            fifo.w_data.eq(camread.pixel_data),
            fifo.w_en.eq(camread.pixel_valid),
            fifo.r_en.eq(1),
            w.en.eq(fifo.r_rdy & (x[:3] == 7) & (y[:3] == 7)),
            w.addr.eq(waddr),
            w.data.eq(fifo.r_data)
        ]

        # Calculate fps of LCD
        count = Signal(25)
        frames = Signal(8)
        fps = Signal(8)
        old_start = Signal()
        cycles = Signal(8)
        cyc_count = Signal(8)

        m.d.sync += [
            old_start.eq((st7789.y == 0) & (st7789.x == 1))
        ]

        with m.If(count == int(platform.default_clk_frequency) - 1):
            m.d.sync += [
                count.eq(0),
                fps.eq(frames),
                frames.eq(0)
            ]
        with m.Else():
            m.d.sync += count.eq(count+1)

        with m.If((st7789.y == 0) & (st7789.x == 1) & ~old_start):
            m.d.sync += [
                frames.eq(frames+1)
            ]

        with m.If(st7789.next_pixel):
            m.d.sync += [
                cyc_count.eq(1),
                cycles.eq(cyc_count)
            ]
        with m.Else():
            m.d.sync += cyc_count.eq(cyc_count+1)

        m.d.comb += leds16.eq(Cat(fps, cycles))

        with m.If(~fifo.w_rdy):
            m.d.sync += led[0].eq(1)

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(ov7670_pmod)    
    platform.add_resources(oled_pmod)
    platform.add_resources(leds8_1_pmod)
    platform.add_resources(leds8_2_pmod)

    platform.build(CamTest(), do_program=True)

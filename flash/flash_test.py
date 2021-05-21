from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        spi_flash = platform.request("spi_flash_1x", 0)
        leds8 = Cat([i for i in platform.request("leds8_1")])

        m = Module()

        dc = Signal(6)
        cmd = Signal(32,reset=0x03000000)
        dat_r = Signal(8)
        delay_cnt = Signal(25)

        with m.FSM() as fsm:
            # Initial delay seems to be necessary before waking flash
            with m.State("RESET"):
                m.d.sync += delay_cnt.eq(delay_cnt+1)
                with m.If(delay_cnt.all()):
                    m.d.sync += spi_flash.cs.o.eq(1)
                    m.next = "POWERUP"
            # Wake up the flash memory
            with m.State("POWERUP"):
                m.d.sync += dc.eq(dc+1)
                m.d.comb += [
                    # SPI clock is out of phase system clock
                    spi_flash.clk.o.eq(~ClockSignal()),
                    spi_flash.copi.o.eq(0xAB >> (7 - dc))
                ]
                with m.If(dc == 7):
                    m.d.sync += spi_flash.cs.o.eq(0)
                with m.Elif(dc == 63): # Delay after wake-up
                    m.d.sync += [
                        dc.eq(31),
                        spi_flash.cs.o.eq(1)
                    ]
                    m.next = "TX"
            # Send a 32-bit command to read from address 0
            with m.State("TX"):
                m.d.sync += dc.eq(dc -1)
                m.d.comb += [
                    spi_flash.copi.o.eq(cmd >> dc),
                    spi_flash.clk.o.eq(~ClockSignal())
                ]
                with m.If(dc == 0):
                    m.d.sync += [
                        dc.eq(7),
                        dat_r.eq(0)
                    ]
                    m.next = "RX"
            # Read a byte from flash
            with m.State("RX"):
                m.d.sync += [
                    dc.eq(dc -1),
                    dat_r.eq(dat_r | (spi_flash.cipo.i << dc))
                ]
                m.d.comb += spi_flash.clk.o.eq(~ClockSignal())
                with m.If(dc == 0):
                    m.d.sync += [
                        dc.eq(7),
                        delay_cnt.eq(0)
                    ]
                    m.next = "SHOW"
            # Show the byte on the led for about a second
            with m.State("SHOW"):
                m.d.sync += delay_cnt.eq(delay_cnt+1)
                with m.If(delay_cnt == 0):
                    m.d.sync += [
                        leds8.eq(dat_r),
                        dat_r.eq(0)
                    ]
                with m.If(delay_cnt.all()):
                    m.next = "RX" # Go on to next byte
            
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)

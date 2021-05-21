from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from spi_controller import SpiController

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        spi_flash = platform.request("spi_flash_1x", 0)
        leds8= Cat([i for i in platform.request("leds8_1")])

        m = Module()

        m.submodules.spi = spi = SpiController(pins=spi_flash, use_csn=False, divisor=5)

        dc = Signal(6)
        delay_cnt = Signal(25)
        n = Signal(16)

        with m.FSM() as fsm:
            with m.State("RESET"):
                # Start-up delay before waking flash is needed
                m.d.sync += delay_cnt.eq(delay_cnt+1)
                with m.If(delay_cnt.all()):
                    m.next = "POWERUP"
            with m.State("POWERUP"):
                # Send wake-up
                m.d.sync += [
                    spi.req.eq(1),
                    # start transaction
                    spi_flash.cs.o.eq(1),
                    spi.din.eq(0xAB)
                ]
                with m.If(spi.done):
                    m.d.sync += [
                        # cancel request during delay
                        spi.req.eq(0),
                        # end transaction
                        spi_flash.cs.o.eq(0)
                    ]
                    # Short delay is needed after start-up
                    m.next = "DELAY1"
            with m.State("DELAY1"):
                m.d.sync += delay_cnt.eq(delay_cnt + 1)
                with m.If(delay_cnt.all()):
                    m.next = "SEND1"
            with m.State("SEND1"):
                m.d.sync += [
                    # Set request and start transcaction to send 0x03000000
                    spi.req.eq(1),
                    spi_flash.cs.eq(1),
                    spi.din.eq(0x03)
                ]
                with m.If(spi.done):
                    m.d.sync += spi.din.eq(0x00)
                    m.next = "SEND2"
            with m.State("SEND2"):
                with m.If(spi.done):
                    m.next = "SEND3"
            with m.State("SEND3"):
                with m.If(spi.done):
                    m.next = "SEND4"
            with m.State("SEND4"):
                with m.If(spi.done):
                    m.next = "READ"
            with m.State("READ"):
                # Don't show zero bytes
                with m.If(spi.done & (spi.dout != 0)):
                    # Cancel request during delay
                    m.d.sync += spi.req.eq(0)
                    m.next = "SHOW"
            with m.State("SHOW"):
                m.d.sync += [
                    leds8.eq(spi.dout),
                    delay_cnt.eq(delay_cnt+1)
                ]
                with m.If(delay_cnt.all()):
                    # Do another read
                    m.d.sync += spi.req.eq(1)
                    m.next = "READ"

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)


from nmigen import *
from nmigen.build import *
from nmigen_stdio.serial import *

from nmigen_boards.blackice_mx import *

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        spi_flash = platform.request("spi_flash_1x", 0)
        leds8 = Cat([i for i in platform.request("leds8_1")])
        uart    = platform.request("uart")
        leds    = Cat([platform.request("led", i) for i in range(4)])
        divisor = int(platform.default_clk_frequency // 115200)

        m = Module()

        # Create the uart
        m.submodules.serial = serial = AsyncSerial(divisor=divisor, pins=uart)

        dc         = Signal(6,  reset=0)
        read_cmd   = Signal(32, reset=0x03000000)
        dat_r      = Signal(8)
        delay_cnt  = Signal(12, reset=0)
        byte_ready = Signal(1,  reset = 0)
        bytes_read = Signal(24, reset=0)
        done       = Signal(1,  reset=0)
        bytes_rcvd = Signal(24, reset=0)
        cmd        = Signal(8,  reset=0)
        length     = Signal(32, reset=0)
        addr       = Signal(32, reset=0)

        # Connect the uart
        m.d.comb += [
            # Connect data out to data in
            serial.tx.data.eq(dat_r),
            # Always allow reads
            serial.rx.ack.eq(1),
            # Write data from flash memory
            byte_ready.eq(0),
            serial.tx.ack.eq(byte_ready),
            # Show any errors on leds: red for parity, green for overflow, blue for frame
            leds.eq(Cat(serial.rx.err.frame, done, serial.rx.err.overflow, serial.rx.err.parity))
        ]

        with m.If(serial.rx.rdy):
            m.d.sync += bytes_rcvd.eq(bytes_rcvd + 1)

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
                        bytes_rcvd.eq(0)
                    ]
                    m.next = "WAITING"
            with m.State("WAITING"):
                # Read the command from the uart
                with m.If(serial.rx.rdy):
                    with m.Switch(bytes_rcvd):
                        with m.Case(0):
                            m.d.sync += cmd.eq(serial.rx.data)
                        with m.Case(1):
                            m.d.sync += length.eq(serial.rx.data)
                        with m.Case(2):
                            m.d.sync += length.eq(Cat(serial.rx.data, length[:24]))
                        with m.Case(3):
                            m.d.sync += length.eq(Cat(serial.rx.data, length[:24]))
                        with m.Case(4):
                            m.d.sync += length.eq(Cat(serial.rx.data, length[:24]))
                        with m.Case(5):
                            m.d.sync += addr.eq(serial.rx.data)
                        with m.Case(6):
                            m.d.sync += addr.eq(Cat(serial.rx.data, addr[:24]))
                        with m.Case(7):
                            m.d.sync += addr.eq(Cat(serial.rx.data, addr[:24]))
                        with m.Case(8):
                            m.d.sync += addr.eq(Cat(serial.rx.data, addr[:24]))
                with m.If(bytes_rcvd == 9):
                    m.d.sync += [
                        dc.eq(31),
                        spi_flash.cs.o.eq(1),
                        bytes_rcvd.eq(0)
                    ]
                    m.next = "READ"
            # Send a 32-bit command to read from address 0
            with m.State("READ"):
                m.d.sync += dc.eq(dc -1)
                m.d.comb += [
                    spi_flash.copi.o.eq((read_cmd | addr) >> dc),
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
                    m.next = "SEND"
            # Show the byte on the led for about a second
            with m.State("SEND"):
                m.d.sync += delay_cnt.eq(delay_cnt+1)
                m.d.comb += byte_ready.eq(delay_cnt == 0) # Strobe to say a byte is ready
                with m.If(delay_cnt == 0):
                    m.d.sync += [
                        dat_r.eq(0),
                        bytes_read.eq(bytes_read + 1),
                        leds8.eq(dat_r)
                    ]
                with m.If(bytes_read == length):
                    m.next="DONE"
                with m.If(delay_cnt.all()):
                    m.next = "RX" # Go on to next byte
            with m.State("DONE"):
                m.d.sync += [
                    done.eq(1)
                ]
            
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)

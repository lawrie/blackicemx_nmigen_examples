from nmigen import *
from nmigen.build import *
from nmigen_stdio.serial import *

from nmigen_boards.blackice_mx import *

from nmigen.lib.fifo import SyncFIFOBuffered

# Optional 8-LED Digilent Pmod for diagnostics
leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# Utility to write data to or read data from the flash memory
# Command comes from the uart in the format: cmd length address
# Where cmd is one byte, 0=read, 1=write, and length and address are 32-bits big-endian
# Data to write then comes from the uart, or data read is send to the uart in binary
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

        dc          = Signal(6,  reset=0)
        read_cmd    = Signal(32, reset=0x03000000)
        write_cmd   = Signal(32, reset=0x02000000)
        erase32_cmd = Signal(32, reset=0x52000000)
        erase64_cmd = Signal(32, reset=0xd8000000)
        we_cmd      = Signal(8 , reset=0x06)
        wake_cmd    = Signal(8 , reset=0xab)
        wait_cmd    = Signal(8 , reset=0x05)
        dat_r       = Signal(8)
        delay_cnt   = Signal(12, reset=0)
        byte_ready  = Signal(1,  reset = 0)
        bytes_read  = Signal(24, reset=0)
        done        = Signal(1,  reset=0)
        bytes_rcvd  = Signal(24, reset=0)
        cmd         = Signal(8,  reset=0)
        length      = Signal(24, reset=0)
        addr        = Signal(24, reset=0)
        rem         = Signal(24, reset=0)
        written     = Signal(24, reset=0)
        erased      = Signal(1,  reset=0)

        # Create fifo from bytes received from uart
        m.submodules.fifo = fifo = SyncFIFOBuffered(width=8,depth=256)

        # Connect the uart
        m.d.comb += [
            # Connect data out to data in
            serial.tx.data.eq(dat_r),
            # Write data from flash memory
            byte_ready.eq(0),
            serial.tx.ack.eq(byte_ready),
            # Write to the FIFO when a byte received from uart
            fifo.w_en.eq(serial.rx.rdy),
            fifo.w_data.eq(serial.rx.data),
            leds8.eq(fifo.r_level),
            # Show any errors on leds: red for parity, green for overflow, blue for frame
            leds.eq(Cat(erased, done, serial.rx.err.overflow, serial.rx.err.parity))
        ]

        # Tally the bytes received from the uart via the fifo
        with m.If(fifo.r_en & fifo.r_rdy):
            m.d.sync += bytes_rcvd.eq(bytes_rcvd + 1)

        # Main state machine
        with m.FSM() as fsm:
            # Initial delay seems to be necessary before waking flash
            with m.State("RESET"):
                m.d.sync += [
                    # Allow reads from uart
                    serial.rx.ack.eq(1),
                    delay_cnt.eq(delay_cnt+1),
                ]
                with m.If(delay_cnt.all()):
                    m.d.sync += spi_flash.cs.o.eq(1)
                    m.next = "POWERUP"
            # Wake up the flash memory
            with m.State("POWERUP"):
                m.d.sync += dc.eq(dc+1)
                m.d.comb += [
                    # SPI clock is out of phase system clock
                    spi_flash.clk.o.eq(~ClockSignal()),
                    spi_flash.copi.o.eq(wake_cmd >> (7 - dc))
                ]
                with m.If(dc == 7):
                    m.d.sync += spi_flash.cs.o.eq(0)
                with m.Elif(dc == 63): # Delay after wake-up
                    m.d.sync += [
                        bytes_rcvd.eq(0),
                        # Read from the uart fifo
                        fifo.r_en.eq(1),
                    ]
                    m.next = "WAITING"
            with m.State("WAITING"):
                # Read the command from the uart fifo
                with m.If(fifo.r_rdy):
                    with m.Switch(bytes_rcvd):
                        with m.Case(0):
                            m.d.sync += cmd.eq(fifo.r_data)
                        with m.Case(1):
                            m.d.sync += length.eq(fifo.r_data)
                        with m.Case(2):
                            m.d.sync += length.eq(Cat(fifo.r_data, length))
                        with m.Case(3):
                            m.d.sync += length.eq(Cat(fifo.r_data, length))
                        with m.Case(4):
                            m.d.sync += addr.eq(fifo.r_data)
                        with m.Case(5):
                            m.d.sync += addr.eq(Cat(fifo.r_data, addr))
                        with m.Case(6):
                            m.d.sync += addr.eq(Cat(fifo.r_data, addr))
                with m.If(bytes_rcvd == 7):
                    with m.If(cmd == 0): # READ
                        m.d.sync += [
                            dc.eq(31),
                            spi_flash.cs.o.eq(1),
                            bytes_rcvd.eq(0),
                            # Stop reading from uart fifo
                            fifo.r_en.eq(0)
                        ]
                        m.next = "READ"
                    with m.Elif(cmd == 1): # WRITE
                        m.d.sync += [
                            dc.eq(0),
                            spi_flash.cs.o.eq(1),
                            rem.eq(length),
                            written.eq(0),
                            # stop reading from uart fifo
                            fifo.r_en.eq(0)
                        ]
                        m.next = "WE1"
            # Send a 32-bit command to read from requested address
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
            # Do a write enable before the erase32
            with m.State("WE1"):
                m.d.sync += dc.eq(dc+1)
                m.d.comb += [
                    spi_flash.clk.o.eq(~ClockSignal()),
                    spi_flash.copi.o.eq(we_cmd >> (7 - dc))
                ]
                with m.If(dc == 7):
                    m.d.sync += [
                        # End of we transaction
                        spi_flash.cs.o.eq(0),
                    ]
                with m.If(dc == 8):
                    m.d.sync += [
                        # Start of Erase 32k transaction
                        spi_flash.cs.o.eq(1),
                        dc.eq(31)
                    ]
                    m.next = "ERASE32"
            # Erase 32K bytes
            with m.State("ERASE32"):
                m.d.sync += dc.eq(dc -1)
                m.d.comb += [
                    spi_flash.copi.o.eq((erase32_cmd | addr) >> dc),
                    spi_flash.clk.o.eq(~ClockSignal())
                ]
                with m.If(dc == 0):
                    m.d.sync += [
                        # End of Erase 32 transaction
                        spi_flash.cs.o.eq(0)
                    ]
                    m.next = "WAIT_ERASE"
            # Wait for erase to complete
            with m.State("WAIT_ERASE"):
                m.d.sync += [
                    dc.eq(0),
                    # Start of wait transaction
                    spi_flash.cs.o.eq(1)
                ]
                m.next = "WAIT_CMD1"
            # Send a wait command
            with m.State("WAIT_CMD1"):
                m.d.sync += dc.eq(dc+1)
                m.d.comb += [
                    spi_flash.clk.o.eq(~ClockSignal()),
                    spi_flash.copi.o.eq(wait_cmd >> (7 - dc))
                ]
                with m.If(dc == 7):
                    m.d.sync += [
                        dat_r.eq(0),
                        dc.eq(7)
                    ]
                    m.next = "WAIT_STATUS1"
            # Read the reply from the wait command
            with m.State("WAIT_STATUS1"):
                m.d.sync += [
                    dc.eq(dc -1),
                    dat_r.eq(dat_r | (spi_flash.cipo.i << dc))
                ]
                m.d.comb += spi_flash.clk.o.eq(~ClockSignal())
                with m.If(dc == 0):
                    m.d.sync += [
                        # End of wait transaction
                        spi_flash.cs.o.eq(0)
                    ]
                    m.next = "CHECK_STATUS1"
            # Check the status from the wait command
            with m.State("CHECK_STATUS1"):
                with m.If(dat_r[0] == 0):
                    m.next = "WRITE256"
                with m.Else():
                    # If not complete, send another wait command
                    m.next = "WAIT_ERASE"
            # Write data in chunks of up to 256 bytes
            with m.State("WRITE256"):
                m.d.sync += erased.eq(~erased)
                # Check for all done
                with m.If(rem == 0):
                    m.next = "DONE"
                with m.Else():
                    m.d.sync += [
                        # Start of write enable transaction
                        spi_flash.cs.o.eq(1),
                        dc.eq(0)
                    ]
                    m.next = "WE2"
            # Do a write enable before the write
            with m.State("WE2"):
                m.d.sync += dc.eq(dc+1)
                m.d.comb += [
                    spi_flash.clk.o.eq(~ClockSignal()),
                    spi_flash.copi.o.eq(we_cmd >> (7 - dc))
                ]
                with m.If(dc == 7):
                    m.d.sync += [
                        # End of we transaction
                        spi_flash.cs.o.eq(0),
                    ]
                with m.If(dc == 8):
                    m.d.sync += [
                        # Start of write address transaction
                        spi_flash.cs.o.eq(1),
                        dc.eq(31)
                    ]
                    m.next = "WRITE"
            # Send a 32-bit command to write data to requested address
            with m.State("WRITE"):
                m.d.sync += dc.eq(dc -1)
                m.d.comb += [
                    spi_flash.copi.o.eq((write_cmd | (addr + written)) >> dc),
                    spi_flash.clk.o.eq(~ClockSignal())
                ]
                with m.If(dc == 0):
                    m.d.sync += [
                        # Read from uart fifo
                        fifo.r_en.eq(1)
                    ]
                    m.next = "GET_BYTE"
            with m.State("GET_BYTE"):
                with m.If(fifo.r_rdy):
                    m.d.sync += [
                        # Get character from uart fifo
                        dat_r.eq(fifo.r_data),
                        # Stop receives from uart fifo again
                        fifo.r_en.eq(0),
                        dc.eq(7)
                    ]
                    #m.d.comb += byte_ready.eq(1) # This echoes to the uart for diagnostics
                    m.next = "TX"
            with m.State("TX"):
                m.d.sync += [
                    dc.eq(dc -1),
                ]
                m.d.comb += [
                    spi_flash.copi.o.eq(dat_r >> dc),
                    spi_flash.clk.o.eq(~ClockSignal())
                ]
                with m.If(dc == 0):
                    m.d.sync += [
                        # Decrement remaining and increment written
                        rem.eq(rem - 1),
                        written.eq(written + 1)
                    ]
                    # Check for written 256 bytes or all done
                    with m.If((rem == 1) | written[:8].all()):
                        m.d.sync += [
                            # End write transaction
                            spi_flash.cs.o.eq(0)
                        ]
                        m.next = "WAIT_WRITE"
                    with m.Else():
                        m.d.sync += [
                            # Read from uart fifo
                            fifo.r_en.eq(1),
                        ]
                        m.next = "GET_BYTE"
            with m.State("WAIT_WRITE"):
                m.d.sync += [
                    dc.eq(0),
                    # Start of wait transaction
                    spi_flash.cs.o.eq(1)
                ]
                m.next = "WAIT_CMD2"
            # Send a wait command
            with m.State("WAIT_CMD2"):
                m.d.sync += dc.eq(dc+1)
                m.d.comb += [
                    spi_flash.clk.o.eq(~ClockSignal()),
                    spi_flash.copi.o.eq(wait_cmd >> (7 - dc))
                ]
                with m.If(dc == 7):
                    m.d.sync += [
                        dat_r.eq(0),
                        dc.eq(7)
                    ]
                    m.next = "WAIT_STATUS2"
            # Read the reply from the wait command
            with m.State("WAIT_STATUS2"):
                m.d.sync += [
                    dc.eq(dc -1),
                    dat_r.eq(dat_r | (spi_flash.cipo.i << dc))
                ]
                m.d.comb += spi_flash.clk.o.eq(~ClockSignal())
                with m.If(dc == 0):
                    m.d.sync += [
                        # End of wait transaction
                        spi_flash.cs.o.eq(0)
                    ]
                    m.next = "CHECK_STATUS2"
            # Check the status from the wait command
            with m.State("CHECK_STATUS2"):
                with m.If(dat_r[0] == 0):
                    m.next = "WRITE256"
                with m.Else():
                    # If not complete, send another wait command
                    m.next = "WAIT_WRITE"
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
            # Transmit the byte with the uart
            with m.State("SEND"):
                m.d.sync += delay_cnt.eq(delay_cnt+1)
                m.d.comb += byte_ready.eq(delay_cnt == 0) # Strobe to say a byte is ready
                with m.If(delay_cnt == 0):
                    m.d.sync += [
                        dat_r.eq(0),
                        bytes_read.eq(bytes_read + 1),
                        # Show the byte on the leds
                        #leds8.eq(dat_r)
                    ]
                with m.If(bytes_read == length):
                    m.next="DONE"
                with m.If(delay_cnt.all()):
                    m.next = "RX" # Go on to next byte
            # Currently stop after one command
            with m.State("DONE"):
                m.d.sync += [
                    done.eq(1)
                ]
            
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.build(Top(), do_program=True)


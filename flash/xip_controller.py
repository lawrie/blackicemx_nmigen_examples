from nmigen import *

class XipController(Elaboratable):
    def __init__(self, width=32):
        # parameters
        self.width  = width

        # inputs
        self.valid  = Signal()
        self.addr   = Signal(24)

        # outputs
        self.dout       = Signal(width)
        self.ready      = Signal()
        self.dout_valid = Signal()

    def elaborate(self, platform):
        spi_flash = platform.request("spi_flash_1x", 0)

        inc = self.width // 8 # width can be 8, 16, 32 or 64
        read_cmd  = 0x03000000

        m = Module()

        dc        = Signal(6, reset=0) # Support width up to 64
        reset_cnt = Signal(10, reset=0)
        next_addr = Signal(24)
        in_trans  = Signal(reset=0)

        m.d.comb += self.dout_valid.eq(0)

        with m.FSM() as fsm:
            # Initial delay seems to be necessary before waking flash
            with m.State("RESET"):
                m.d.sync += reset_cnt.eq(reset_cnt+1)
                with m.If(reset_cnt.all()):
                    # Start transaction
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
                    m.next = "WAITING"
            # Wait for a command
            with m.State("WAITING"):
                with m.If(self.valid):
                    with m.If(in_trans & (self.addr == next_addr)):
                        m.d.sync += [
                            dc.eq(self.width - 1),
                            self.dout.eq(0)
                        ]
                        m.next = "RX"
                    with m.Else():
                        # End any existing transaction
                        m.d.sync += [
                            next_addr.eq(self.addr),
                            spi_flash.cs.o.eq(0)
                        ]
                        m.next = "READ"
            # Start a read transaction
            with m.State("READ"):
                m.d.sync += [
                    dc.eq(31),
                    spi_flash.cs.o.eq(1),
                    in_trans.eq(1)
                ]
                m.next = "READ_CMD"
            # Send a command to read from specified address
            with m.State("READ_CMD"):
                m.d.sync += dc.eq(dc -1)
                m.d.comb += [
                    spi_flash.copi.o.eq((read_cmd | next_addr) >> dc),
                    spi_flash.clk.o.eq(~ClockSignal())
                ]
                with m.If(dc == 0):
                    m.d.sync += [
                        dc.eq(self.width - 1),
                        self.dout.eq(0)
                    ]
                    m.next = "RX"
            # Read data from flash
            with m.State("RX"):
                m.d.sync += [
                    dc.eq(dc -1),
                    self.dout.eq(self.dout | (spi_flash.cipo.i << dc))
                ]
                m.d.comb += spi_flash.clk.o.eq(~ClockSignal())
                with m.If(dc == 0):
                    m.next = "DONE"
            with m.State("DONE"):
                m.d.comb += self.dout_valid.eq(1)
                m.d.sync += next_addr.eq(next_addr + inc)
                m.next = "WAITING"
            
        m.d.comb += self.ready.eq(fsm.ongoing("WAITING"))

        return m


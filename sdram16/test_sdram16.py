from nmigen import *
from nmigen.build import *
from sdram_controller16 import sdram_controller
from pll import PLL

# Diglient 8-LED Pmods for diagnostics 
leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

leds8_2_pmod = [
    Resource("leds8_2", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# Test of 16-bit SDRAM controller
class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        # Get pins
        led = [platform.request("led",count) for count in range(4)]
        leds = Cat([i.o for i in led])
        leds8_1 = platform.request("leds8_1")
        leds8_2 = platform.request("leds8_2")
        led16 =  [i for i in leds8_1] + [i for i in leds8_2]
        leds16 = Cat([i for i in led16])
        clk_in = platform.request(platform.default_clk, dir='-')[0]

        # Clock generation
        # PLL - 64MHz for sdram
        m.submodules.pll = pll = PLL(freq_in_mhz=25, freq_out_mhz=64, domain_name="sdram")

        m.domains.sdram = cd_sdram = pll.domain
        m.d.comb += pll.clk_pin.eq(clk_in)

        # Divide clock by 8
        div = Signal(3)
        m.d.sdram += div.eq(div+1)

        # Make sync domain 8MHz
        m.domains.sync = cd_sync = ClockDomain("sync")
        m.d.comb += ClockSignal().eq(div[2])

        # Power-on reset (not used)
        reset = Signal(10, reset=0)
        with m.If(~reset.all()):
            m.d.sync += reset.eq(reset+1)

        # Add the SDRAM controller
        m.submodules.mem = mem = sdram_controller()

        # RAM test
        addr   = Signal(20, reset=0) # word address
        din    = Signal(16)          # data to be written to SDRAM
        count  = Signal(5,  reset=0) # width control speed of read back
        we     = Signal(1,  reset=0) # request write
        oe     = Signal(1,  reset=0) # request read
        read   = Signal(1,  reset=0) # Set for read back phase
        err    = Signal(1,  reset=0) # Set when error is detected
        passed = Signal(1,  reset=0) # Set if test passed

        m.d.comb += [
            mem.init.eq(~pll.locked), # Use pll not locked as signal to initialise SDRAM 
            mem.sync.eq(div[2]),      # Sync with 8MHz clock
            mem.address.eq(addr),
            mem.data_in.eq(din),
            mem.req_read.eq(oe),
            mem.req_write.eq(we),
            din.eq(addr[4:]),         # Write most significant 16 bits of address
            leds16.eq(mem.data_out)   # Put the data read on the debugg leds
        ]

        # Set the error flag if read gives the wrong value
        with m.If((count > 0) & read & (mem.data_out != addr[4:])):
            m.d.sync += err.eq(1)

        # Increment count and do transfer when count is 0
        m.d.sync += [
            count.eq(count+1),
            we.eq((count == 0) & ~read),
            oe.eq((count == 0) & read)
        ]

        # Increment address every other cycle for write or when
        # count is exhausted for reads
        with m.If((~read & (count == 1)) | count.all()):
            with m.If(~read & (count == 1)):
                m.d.sync += count.eq(0)

            m.d.sync += addr.eq(addr+1)

            with m.If(addr.all()):
                # Switch to read when all data is written
                m.d.sync += read.eq(1)

                # Set passed flag when all data has been read without an error
                with m.If(read & ~err):
                    m.d.sync += passed.eq(1)

        # Show flags on the leds
        # Blue led on during write phase, green led means passed, red means error
        m.d.comb += leds.eq(Cat([~read, passed, C(0,1), err]))

        return m

if __name__ == "__main__":
    from nmigen_boards.blackice_mx import BlackIceMXPlatform

    platform = BlackIceMXPlatform()

    platform.add_resources(leds8_1_pmod)
    platform.add_resources(leds8_2_pmod)

    platform.build(Top(), do_program=True)


from nmigen import *
from debouncer import Debouncer
from sdram_controller16 import sdram_controller
from pll import PLL

class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        led = [platform.request("led",count) for count in range(4)]
        leds = Cat([i.o for i in led])
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

        reset = Signal(10, reset=0)
        with m.If(~reset.all()):
            m.d.sync += reset.eq(reset+1)

        # Add the SDRAM controller
        m.submodules.mem = mem = sdram_controller()

        addr = Signal(20) # word address
        din = Signal(16)   # data to be written to SDRAM

        m.d.comb += [
            mem.init.eq(~reset.all()),
            mem.address.eq(addr),
            mem.data_in.eq(din),
            mem.sync.eq(div[2])
        ]

        # Writes and reads
        cnt = Signal(20)

        m.d.sync += [
            cnt.eq(cnt + 1),
            mem.req_write.eq(0),
            mem.req_read.eq(0)
        ]

        with m.If(cnt == 100):
            m.d.sync += [
                mem.req_write.eq(1),
                din.eq(0x0102),
                addr.eq(100)
            ]
        with m.If(cnt == 200):
            m.d.sync += [
                mem.req_write.eq(1),
                din.eq(0x0304),
                addr.eq(101)
            ]
        with m.If(cnt == 300):
            m.d.sync += [
                mem.req_read.eq(1),
                addr.eq(100)
            ]

        # Show 3 bits of data from SDRAM on the leds
        m.d.comb += leds.eq(mem.data_out)

        return m

if __name__ == "__main__":
    from nmigen_boards.blackice_mx import BlackIceMXPlatform
    platform = BlackIceMXPlatform()
    platform.build(Top(), do_program=True)


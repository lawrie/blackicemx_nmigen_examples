from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from nmigen_soc import wishbone
from lambdasoc.periph.sram import SRAMPeripheral
#from sram import SRAMPeripheral

from readhex import readhex

leds8_1_pmod = [
    Resource("leds8_1", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",2)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

leds8_2_pmod = [
    Resource("leds8_2", 0,
            Subsignal("leds", Pins("7 8 9 10 1 2 3 4", dir="o", conn=("pmod",3)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

# Tiny CPU converted from Verilog - https://github.com/jbush001/MiteCPU
class MiteCPU(Elaboratable):
    def __init__(self):
        self._arbiter = wishbone.Arbiter(addr_width=11, data_width=16, granularity=16)
        self._decoder = wishbone.Decoder(addr_width=11, data_width=16, granularity=16, features={"cti", "bte"})

        self.code = SRAMPeripheral(size=256, data_width=16, granularity=16, writable=False)
        self.data = SRAMPeripheral(size=256, data_width=16)

        self._decoder.add(self.code.bus, addr=0x0000)
        self._decoder.add(self.data.bus, addr=0x0100)

    def elaborate(self, platform):
        leds    = Cat([platform.request("led", i) for i in range(4)])
        leds8_1 = Cat([i for i in platform.request("leds8_1")])
        leds8_2 = Cat([i for i in platform.request("leds8_2")])

        # Read in program and print it in hex
        prog = readhex()
        print(" ".join(hex(n) for n in prog))

        # Registers and other signals
        ip     = Signal(8,  reset=0xff) # Instruction pointer
        ip_nxt = Signal(8)              # Next instruction pointer
        instr  = Signal(11)             # Current instruction
        acc    = Signal(8,  reset=0)    # Accumulator
        index  = Signal(8,  reset=0)    # Index register
        op     = Signal(8)              # The data operand
        addr   = Signal(8)              # The data address
        dc     = Signal(22)

        m = Module()

        # Code and data wishbone peripherals
        m.submodules.code = code = self.code
        m.submodules.data = data = self.data

        # Decoder and arbiter
        #m.submodules.decoder = self._decoder
        m.submodules.arbiter = self._arbiter

        # Initialise the rom with code
        code.init = prog

        # Connect memory and calculate data address and next instruction pointer
        m.d.comb += [
            code.bus.adr.eq(ip),
            code.bus.cti.eq(wishbone.CycleType.CLASSIC),
            data.bus.dat_w.eq(acc),
            data.bus.adr.eq(addr),
            data.bus.sel.eq(1),
            addr.eq(instr[:8] + index),
            ip_nxt.eq(Mux((instr[8:] == 4) & acc[7], instr[:8], ip + 1)),
            leds8_1.eq(ip),
            leds8_2.eq(instr[8:])
        ]

        # Execution state machine
        with m.FSM() as fsm:
            with m.State("FETCH"):
                with m.If(code.bus.ack):
                    m.d.sync += instr.eq(code.bus.dat_r)
                    m.next = "DATA"
            with m.State("DATA"):
                with m.If(data.bus.ack):
                    m.d.sync += op.eq(data.bus.dat_r)
                    m.next = "EXECUTE"
            with m.State("EXECUTE"):
                # Delay execution for led diagnostics
                m.d.sync += dc.eq(dc + 1)
                with m.If(dc.all()):
                    # Advance instruction pointer
                    m.d.sync += ip.eq(ip_nxt)
            
                    # Decode and execute current instruction
                    m.d.sync += index.eq(0) # index defaults to zero
                    with m.Switch(instr[8:]):
                        with m.Case("000"):
                            m.d.sync += acc.eq(acc + op)
                        with m.Case("001"):
                            m.d.sync += acc.eq(acc - op)
                        with m.Case("110"):
                            m.d.sync += acc.eq(acc & op)
                        with m.Case("010"):
                            m.d.sync += acc.eq(instr[:8])
                        with m.Case("101"):
                            m.d.sync += index.eq(op)
                        with m.Case("011"):
                            # data[0] is leds
                            with m.If(instr[:8] == 0):
                                m.d.sync += leds.eq(acc)
                    m.next = "FETCH"

        # Set requests for code and data on appropriate cycles
        m.d.comb += [
            code.bus.cyc.eq(fsm.ongoing("FETCH")),
            code.bus.stb.eq(code.bus.cyc),
            data.bus.cyc.eq(fsm.ongoing("DATA")),
            data.bus.stb.eq(data.bus.cyc),
            data.bus.we.eq(instr[8:] == 0b011)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(leds8_1_pmod)
    platform.add_resources(leds8_2_pmod)
    platform.build(MiteCPU(), nextpnr_opts="--timing-allow-fail", do_program=True)


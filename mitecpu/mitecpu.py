from nmigen import *
from nmigen_boards.blackice_mx import *

from readhex import readhex

# Tiny CPU converted from Verilog - https://github.com/jbush001/MiteCPU
class MiteCPU(Elaboratable):
    def elaborate(self, platform):
        leds   = Cat([platform.request("led", i) for i in range(4)])

        # Read in program and print it in hex
        prog = readhex()
        print(" ".join(hex(n) for n in prog))

        # Code and data storage
        code = Memory(width=11, depth=256, init=prog)
        data = Memory(width=8, depth=256)

        # Registers and other signals
        ip     = Signal(8,  reset=0xff) # Instruction pointer
        ip_nxt = Signal(8)              # Next instruction pointer
        instr  = Signal(11, reset=0)    # Current instruction
        acc    = Signal(8,  reset=0)    # Accumulator
        index  = Signal(8,  reset=0)    # Index register
        op     = Signal(8,  reset=0)    # The operand
        addr   = Signal(8)              # Address
        delay  = Signal(22)             # Delay counter

        m = Module()

        # Create negedge domain
        neg = ClockDomain("neg", clk_edge="neg")
        m.domains += neg
        m.d.comb += neg.clk.eq(ClockSignal())
       
        # Set address 
        m.d.comb += addr.eq(instr[:8] + index)

        # Set ip_nxt
        m.d.comb += ip_nxt.eq(Mux((instr[8:] == 4) & acc[7], instr[:8], ip + 1))

        # Delay counter to execute slowly and see result on leds
        m.d.sync += delay.eq(delay + 1)

        with m.If(delay == 0):
            # Advance instruction pointer
            m.d.sync += ip.eq(ip_nxt)
            
            # Fetch next instruction
            m.d.sync += instr.eq(code[ip_nxt])

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
                    m.d.sync += data[addr].eq(acc)
                    # data[0] is leds
                    with m.If(instr[:8] == 0):
                        m.d.sync += leds.eq(acc)
           
            # Fetch the operand on the negative edge of clock
            m.d.neg += op.eq(data[addr])
        
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(MiteCPU(), nextpnr_opts="--timing-allow-fail", do_program=True)


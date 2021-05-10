from nmigen import *

# Dual-port SDRAM controller with 8-bit reads and writes
class Sdram(Elaboratable):
    def __init__(self):

        # Chip interface
        self.sd_data_in  = Signal(16)
        self.sd_data_out = Signal(16)
        self.sd_addr     = Signal(11)
        self.sd_dqm      = Signal(2)
        self.sd_ba       = Signal(1)
        self.sd_cs       = Signal()
        self.sd_we       = Signal()
        self.sd_ras      = Signal()
        self.sd_cas      = Signal()

        # Control
        self.init        = Signal()
        self.clkref      = Signal()
        self.we_out      = Signal()

        # Port A
        self.addrA       = Signal(21) # Byte address
        self.weA         = Signal()
        self.dinA        = Signal(8)
        self.oeA         = Signal()
        self.doutA       = Signal(8)

        # Port B
        self.addrB       = Signal(21) # Byte address
        self.weB         = Signal()
        self.dinB        = Signal(8)
        self.oeB         = Signal()
        self.doutB       = Signal(8)
        
    def elaborate(self, platform):

        m = Module()

        # Configure SDRAM access
        RASCAS_DELAY   = C(2,3)
        BURST_LENGTH   = C(0,3)
        ACCESS_TYPE    = C(0,1)
        CAS_LATENCY    = C(2,3)
        OP_MODE        = C(0,2)
        NO_WRITE_BURST = C(1,1)

        MODE = Cat([BURST_LENGTH, ACCESS_TYPE, CAS_LATENCY, OP_MODE, NO_WRITE_BURST, C(0,1)])

        # States
        STATE_FIRST     = C(0,3)
        STATE_CMD_START = C(1,3)
        STATE_CMD_CONT  = STATE_CMD_START + RASCAS_DELAY
        STATE_CMD_READ  = STATE_CMD_CONT + CAS_LATENCY + C(1,3)
        STATE_CMD_HIGHZ = STATE_CMD_READ - C(1,3)
        STATE_LAST      = C(7,3)

        # Save clkref to detect change, and increment state (q)
        clkref_last = Signal()
        q           = Signal(3)

        m.d.sdram += [
            clkref_last.eq(self.clkref),
            q.eq(q+1)
        ]

        with m.If(q == STATE_LAST):
            m.d.sdram += q.eq(STATE_FIRST)
        with m.If(~clkref_last & self.clkref):
            m.d.sdram += q.eq(STATE_FIRST+1)

        # Reset counts down after init set
        reset = Signal(5)

        with m.If(self.init):
            m.d.sdram += reset.eq(C(0x1f,5))
        with m.Elif((q == STATE_LAST) & (reset != 0)):
            m.d.sdram += reset.eq(reset-1)

        # SDRAM commands
        CMD_INHIBIT          = C(0b1111,4)
        CMD_NOP              = C(0b0111,4)
        CMD_ACTIVE           = C(0b0011,4)
        CMD_READ             = C(0b0101,4)
        CMD_WRITE            = C(0b0100,4)
        CMD_BURST_TERMINATE  = C(0b0110,4)
        CMD_PRECHARGE        = C(0b0010,4)
        CMD_AUTO_REFRESH     = C(0b0001,4)
        CMD_LOAD_MODE        = C(0b0000,4)

        sd_cmd = Signal(4)
        oe     = Signal()
        addr   = Signal(21) # Byte address
        din    = Signal(8)
        addr0  = Signal()
        
        # clkref chooses which port to use
        with m.If(self.clkref):
            m.d.comb += [
                oe.eq(self.oeA),
                self.we_out.eq(self.weA),
                addr.eq(self.addrA),
                din.eq(self.dinA)
            ]
        with m.Else():
            m.d.comb += [
                oe.eq(self.oeB),
                self.we_out.eq(self.weB),
                addr.eq(self.addrB),
                din.eq(self.dinB)
            ]

        # Latch address 0
        with m.If((q == 1) & oe):
            m.d.sdram += addr0.eq(addr[0])

        # Choose which half of 16-bit word to write
        dout = Signal(8)

        m.d.comb += dout.eq(Mux(addr0, self.sd_data_in[0:8], self.sd_data_in[8:]))

        # State machine
        with m.If(q == STATE_CMD_READ):
            # Choose port to read into
            with m.If(self.oeA & self.clkref):
                m.d.sdram += self.doutA.eq(dout)
            with m.If(self.oeB & ~self.clkref):
                m.d.sdram += self.doutB.eq(dout)

        # Set the command for reset or run
        reset_cmd = Signal(4)
        run_cmd   = Signal(4)

        m.d.comb += [
            # Reset cmd
            reset_cmd.eq(Mux((q == STATE_CMD_START) & (reset == 13), CMD_PRECHARGE,
                         Mux((q == STATE_CMD_START) & (reset == 2), CMD_LOAD_MODE, CMD_INHIBIT))),
            # Run cmd
            run_cmd.eq(Mux((self.we_out | oe) & (q == STATE_CMD_START), CMD_ACTIVE, 
                       Mux(self.we_out & (q == STATE_CMD_CONT), CMD_WRITE,
                       Mux(~self.we_out & oe & (q == STATE_CMD_CONT), CMD_READ,
                       Mux(~self.we_out & ~oe & (q == STATE_CMD_START), CMD_AUTO_REFRESH, CMD_INHIBIT))))),
            # Set cmd
            sd_cmd.eq(Mux(reset != 0, reset_cmd, run_cmd))
        ]

        # Set the address for reset or run
        reset_addr = Signal(11)
        run_addr = Signal(11)

        m.d.comb += [
            # Reset address
            reset_addr.eq(Mux(reset == 13, C(0b10000000000,11), MODE)), # Precharge all banks
            # Run address
            run_addr.eq(Mux(q == STATE_CMD_START, addr[8:19], Cat(addr[1:9], C(0b100,3))))
        ]

        # Assign chip pins
        m.d.comb += [
            self.sd_data_out.eq(Mux(self.we_out, Cat(din, din), C(0,16))),
            self.sd_addr.eq(Mux(reset != 0, reset_addr, run_addr)),
            self.sd_ba.eq(Mux(reset != 0, C(0,1), addr[19])),
            # Set DQ mask to write either odd or even byte
            self.sd_dqm.eq(Mux(self.we_out, Cat(~addr[0], addr[0]), C(0,2))),
            self.sd_cs.eq(sd_cmd[3]),
            self.sd_ras.eq(sd_cmd[2]),
            self.sd_cas.eq(sd_cmd[1]),
            self.sd_we.eq(sd_cmd[0])
        ]

        return m


from nmigen import *
from nmigen.utils import bits_for

class I2cMaster(Elaboratable):
    def __init__(self):
        # inputs
        self.valid     = Signal()
        self.read      = Signal()
        self.rep_read  = Signal()
        self.short_wr  = Signal()
        self.addr      = Signal(7)
        self.reg       = Signal(8)
        self.din       = Signal(8)
        self.din2      = Signal(8)

        # outputs
        self.rdy       = Signal()
        self.dout      = Signal(8)
        self.init      = Signal(reset=1)
        self.addr_nack = Signal()
        self.data_nack = Signal()
        self.diag      = Signal(8)

    def elaborate(self, platform):
        # Get i2c pins in direct mode
        dir_dict = { "scl":"-", "sda":"-"}
        i2c_pins = platform.request("i2c", dir=dir_dict)

        m = Module()

        # Set direction of i2c pins
        scl_dir = Signal()
        scl_out = Signal()
        scl_in  = Signal()

        scl_io = Instance("SB_IO",
            p_PIN_TYPE=C(0b1010_01, 6),
            p_PULLUP=C(1),
            io_PACKAGE_PIN=i2c_pins.scl,
            i_OUTPUT_ENABLE=scl_dir,
            i_D_OUT_0=scl_out,
            o_D_IN_0=scl_in)

        m.submodules += scl_io

        sda_dir = Signal()
        sda_out = Signal()
        sda_in = Signal()

        sda_io = Instance("SB_IO",
            p_PIN_TYPE=C(0b1010_01, 6),
            p_PULLUP=C(1),
            io_PACKAGE_PIN=i2c_pins.sda,
            i_OUTPUT_ENABLE=sda_dir,
            i_D_OUT_0=sda_out,
            o_D_IN_0=sda_in)

        m.submodules += sda_io

        m.d.comb += [
            scl_out.eq(~scl_dir),
            sda_out.eq(~sda_dir)
        ]

        # De-glitch i2c pins
        sda_sr = Signal(4, reset=0b1111)
        scl_sr = Signal(4, reset=0b1111)
        sda    = Signal(reset=1)
        scl    = Signal(reset=1)

        m.d.sync += [
            sda_sr.eq(Cat(sda_in, sda_sr[:3])),
            scl_sr.eq(Cat(scl_in, scl_sr[:3]))
        ]

        with m.If(sda_sr == C(0b0000,4)):
            m.d.sync += sda.eq(0)
        with m.Elif(sda_sr == C(0b1111,4)):
            m.d.sync += sda.eq(1)

        with m.If(scl_sr == C(0b0000,4)):
            m.d.sync += scl.eq(0)
        with m.Elif(scl_sr == C(0b1111,4)):
            m.d.sync += scl.eq(1)

        # State machine states
        PRE_START_UP = 0
        START_UP     = 1
        IDLE         = 2
        START        = 3
        CLOCK_LOW    = 4
        SHIFT_DATA   = 5
        CLOCK_HIGH   = 6
        STOP         = 7
        SPIN         = 15

        state     = Signal(4, reset=PRE_START_UP)
        rtn_state = Signal(4)

        m.d.comb += self.diag.eq(Cat(state, rtn_state))

        # i2c timings
        FREQ       = int(platform.default_clk_frequency // 1000000)
        #FREQ       = 22
        T_HD_STA   = 4 * FREQ
        T_LOW      = 5 * FREQ
        T_HIGH     = 5 * FREQ
        T_SU_STA   = 5 * FREQ
        T_SU_DAT   = (FREQ >> 2) + 1
        T_HOLD     = (FREQ >> 1) + 1
        T_SU_STO   = 4 * FREQ

        # Timers and other signals
        timer             = Signal(bits_for(T_LOW + 1), reset=T_LOW)
        bit_count         = Signal(6)
        scl_startup_count = Signal(4)
        wr_cyc            = Signal()
        shift_reg         = Signal(36)
        read_data         = Signal(8)

        # State machine
        with m.Switch(state):
            with m.Case(PRE_START_UP):
                with m.If(timer == 0):
                    with m.If(~scl_dir):
                        with m.If(sda & (scl_startup_count == 12)):
                            m.d.sync += [
                                scl_startup_count.eq(0),
                                state.eq(START_UP)
                            ]
                        with m.Else():
                            m.d.sync += [
                                scl_dir.eq(1),
                                scl_startup_count.eq(scl_startup_count + 1),
                                timer.eq(T_LOW)
                            ]
                    with m.Else():
                        m.d.sync += [
                            scl_dir.eq(0),
                            timer.eq(T_LOW)
                        ]
                with m.Elif(scl | scl_dir):
                    m.d.sync += timer.eq(timer - 1)
            with m.Case(START_UP):
                with m.If(timer == 0):
                    m.d.sync += [
                        timer.eq(T_LOW),
                        scl_startup_count.eq(scl_startup_count + 1)
                    ]
                    with m.If(scl_startup_count == 2):
                        m.d.sync += sda_dir.eq(1)
                    with m.If(scl_startup_count == 12):
                        m.d.sync += sda_dir.eq(0)
                    with m.If(scl_startup_count == 15):
                        m.d.sync += state.eq(IDLE)
                with m.Else():
                    m.d.sync += timer.eq(timer - 1)
            with m.Case(IDLE):
                m.d.sync += [
                    sda_dir.eq(0),
                    scl_dir.eq(0),
                    self.rdy.eq(1),
                    self.init.eq(0)
                ]
                with m.If(self.valid):
                    m.d.sync += [
                    self.rdy.eq(0),
                    state.eq(START),
                    wr_cyc.eq(1)
                ]
            with m.Case(START):
                m.d.sync += [
                    sda_dir.eq(1),
                    scl_dir.eq(0)
                ]
                with m.If(~sda):
                    with m.If(self.read):
                        with m.If(wr_cyc):
                            m.d.sync += shift_reg.eq(Cat([C(0,17), self.rep_read, C(1,1), self.reg, C(1,0), C(0,0), self.addr]))
                        with m.Else():
                            m.d.sync += shift_reg.eq(Cat([C(0,18), C(0,1), C(0xff,8),C(1,1),C(1,1),self.addr]))
                    with m.Else():
                        m.d.sync += shift_reg.eq(Cat([C(1,1), self.din2, C(1,1), self.din, C(1,1), self.reg, C(1,1), C(0,1), self.addr]))
                    m.d.sync += [
                        bit_count.eq(0),
                        timer.eq(T_HD_STA),
                        rtn_state.eq(CLOCK_LOW),
                        state.eq(SPIN)
                    ]
            with m.Case(CLOCK_LOW):
                m.d.sync += scl_dir.eq(1)
                with m.If(~scl):
                    m.d.sync += [
                        timer.eq(T_HOLD),
                        rtn_state.eq(SHIFT_DATA),
                        state.eq(SPIN)
                    ]
            with m.Case(SHIFT_DATA):
                m.d.sync += [
                    sda_dir.eq(~shift_reg[-1]),
                    shift_reg.eq(Cat(C(0,1), shift_reg[:-1])),
                    timer.eq(T_LOW),
                    rtn_state.eq(CLOCK_HIGH),
                    state.eq(SPIN)
                ]
            with m.Case(CLOCK_HIGH):
                m.d.sync += scl_dir.eq(0)
                with m.If(scl):
                    m.d.sync += bit_count.eq(bit_count + 1)
                    with m.If(bit_count == 8):
                        m.d.sync += self.addr_nack.eq(sda)
                    with m.Elif(((bit_count == 17) & wr_cyc) | (bit_count == 26) | (bit_count == 35)):
                        m.d.sync += self.data_nack.eq(sda)
                    with m.If(((bit_count == 18) & self.read) | (bit_count == 36) | (self.short_wr & (bit_count == 27))):
                        m.d.sync += [
                            timer.eq(T_SU_STO),
                            rtn_state.eq(STOP),
                            state.eq(SPIN)
                        ]
                    with m.Else():
                        with m.If(bit_count != 17):
                            m.d.sync += read_data.eq(Cat(sda,read_data[:7]))
                        m.d.sync += [
                            timer.eq(T_HIGH),
                            rtn_state.eq(CLOCK_LOW),
                            state.eq(SPIN)
                        ]
            with m.Case(STOP):
                m.d.sync += sda_dir.eq(0)
                with m.If(sda):
                    with m.If(self.read):
                        with m.If(wr_cyc):
                            # TODO repeated read
                            m.d.sync += [
                                timer.eq(T_SU_STA),
                                rtn_state.eq(START),
                                state.eq(SPIN)
                            ]
                        with m.Else():
                            m.d.sync += [
                                self.dout.eq(read_data),
                                timer.eq(T_SU_STA),
                                rtn_state.eq(IDLE),
                                state.eq(SPIN)
                            ]
                    with m.Else():
                        m.d.sync += [
                            timer.eq(T_SU_STA),
                            rtn_state.eq(IDLE),
                            state.eq(SPIN)
                        ]
            with m.Case(SPIN):
                with m.If(timer > 0):
                    m.d.sync += timer.eq(timer - 1)
                with m.Else():
                    m.d.sync += state.eq(rtn_state)

        return m


from nmigen import *
from math import ceil, log2

class Ping(Elaboratable):
    def __init__(self):
        # inputs
        self.req       = Signal()
        self.echo      = Signal()
        # outputs
        self.trig      = Signal(reset=0)
        self.done      = Signal(reset=0)
        self.val       = Signal(8, reset=0)

    def elaborate(self, platform):
        m = Module()

        CLK_FREQ = int(platform.default_clk_frequency)
        print("clk freq:", CLK_FREQ)

        CLKS_PER_MICRO = int(CLK_FREQ/1000000)
        print("clks per microsecond:", CLKS_PER_MICRO)
        
        TIMEOUT = 10000 * CLKS_PER_MICRO
        print("timeout:", TIMEOUT)

        CNT_BITS = ceil(log2(TIMEOUT + 1))
        print("cnt bits:", CNT_BITS)

        TRIG_LOW_CYCLES = 2 * CLKS_PER_MICRO
        print("trig low cycles:", TRIG_LOW_CYCLES)

        TRIG_HIGH_CYCLES = 10 * CLKS_PER_MICRO
        print("trig high cycles:", TRIG_HIGH_CYCLES)

        # Speed of sound in cm/s * 2 = 58.3
        CM_CYCLES = int(58.3 * CLKS_PER_MICRO)
        print("cm cycles:", CM_CYCLES)

        CM_CNT_BITS = ceil(log2(CM_CYCLES))
        print("cm cnt bits:", CM_CNT_BITS)

        cnt    = Signal(CNT_BITS, reset=0)
        cm_cnt = Signal(CM_CNT_BITS)
        
        STATE_WAITING   = 0
        STATE_TRIG_LOW  = 1
        STATE_TRIG_HIGH = 2
        STATE_ECHO_LOW  = 3
        STATE_ECHO_HIGH = 4
        STATE_MEASURE   = 5

        state = Signal(3, reset=STATE_WAITING)

        # Timeout if count goes too high in any state
        with m.If(cnt == TIMEOUT):
            m.d.sync += [
                self.done.eq(1),
                # Return 255 if error
                self.val.eq(255),
                cnt.eq(0),
                self.trig.eq(0),
                state.eq(STATE_WAITING)
            ]
        # increment count if active
        with m.Elif(state != STATE_WAITING):
            m.d.sync += cnt.eq(cnt + 1)

        # State machine
        with m.Switch(state):
            # Wait for request
            with m.Case(STATE_WAITING):
                with m.If(self.req):
                    m.d.sync += [
                        self.trig.eq(0),
                        self.val.eq(0),
                        self.done.eq(0),
                        state.eq(STATE_TRIG_LOW)
                    ]
            # Set trigger low for 2 microseconds
            with m.Case(STATE_TRIG_LOW):
                with m.If(cnt == TRIG_LOW_CYCLES):
                    m.d.sync += [
                        self.trig.eq(1),
                        cnt.eq(0),
                        state.eq(STATE_TRIG_HIGH)
                    ]
            # Set trigger high for 10 microseconds
            with m.Case(STATE_TRIG_HIGH):
                with m.If(cnt == TRIG_HIGH_CYCLES):
                    m.d.sync += [
                        self.trig.eq(0),
                        cnt.eq(0),
                        state.eq(STATE_ECHO_LOW)
                    ]
            # Ensure echo is low
            with m.Case(STATE_ECHO_LOW):
                with m.If(self.echo == 0):
                    m.d.sync += [
                        cnt.eq(0),
                        state.eq(STATE_ECHO_HIGH)
                    ]
            # Wait for echo to go high
            with m.Case(STATE_ECHO_HIGH):
                with m.If(self.echo == 1):
                    m.d.sync += [
                        cnt.eq(0),
                        cm_cnt.eq(0),
                        state.eq(STATE_MEASURE)
                    ]
            # Take measurement by waiting for echo to go low
            with m.Case(STATE_MEASURE):
                # Count centimetres travelled
                with m.If(cm_cnt == CM_CYCLES):
                    m.d.sync += [
                        self.val.eq(self.val + 1),
                        cm_cnt.eq(0)
                    ]
                with m.Else():
                    m.d.sync += cm_cnt.eq(cm_cnt + 1)

                with m.If(self.echo == 0):
                    m.d.sync += [
                        cnt.eq(0),
                        # Set done when measurement complete
                        self.done.eq(1),
                        state.eq(STATE_WAITING)
                    ]

        return m


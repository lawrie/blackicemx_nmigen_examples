from nmigen import *
from math import ceil, log2

class WS2812(Elaboratable):
    def __init__(self, NUM_LEDS=16):
        #parameters
        self.NUM_LEDS = NUM_LEDS
        # inputs
        self.rgb_data = Signal(24)
        self.led_num  = Signal(8)
        self.write    = Signal()
        # outputs
        self.data     = Signal(8, reset=0)

    def elaborate(self, platform):
        m = Module()

        LED_BITS = ceil(log2(self.NUM_LEDS))

        CLK_MHZ = int(platform.default_clk_frequency / 1000000)

        T_ON = ceil(CLK_MHZ*800/1000)
        T_OFF = ceil(CLK_MHZ*400/1000)
        T_RESET = ceil(CLK_MHZ*65)
        T_PERIOD = ceil(CLK_MHZ*1200/1000)

        COUNT_BITS = ceil(log2(T_RESET))

        led_reg = Memory(width=24, depth=self.NUM_LEDS)
        m.submodules.r = r = led_reg.read_port()
        m.submodules.w = w = led_reg.write_port()

        led_counter = Signal(LED_BITS, reset=self.NUM_LEDS -1)
        bit_counter = Signal(COUNT_BITS, reset=T_RESET)
        rgb_counter = Signal(5, reset=23)
    
        STATE_DATA  = 0
        STATE_RESET = 1

        state     = Signal(1,  reset=STATE_RESET)
        led_color = Signal(24, reset=0)

        m.d.comb += [
            w.addr.eq(self.led_num),
            w.data.eq(self.rgb_data),
            r.addr.eq(led_counter),
            led_color.eq(r.data)
        ]

        with m.If(self.write):
            m.d.sync += w.en.eq(1)

        with m.If(state == STATE_RESET):
            m.d.sync += [
                rgb_counter.eq(23),
                led_counter.eq(self.NUM_LEDS - 1),
                self.data.eq(0),
                bit_counter.eq(bit_counter - 1)
            ]

            with m.If(bit_counter == 0):
                m.d.sync += [
                    state.eq(STATE_DATA),
                    bit_counter.eq(T_PERIOD)
                ]
        
        with m.If(state == STATE_DATA):
            with m.If(led_color.bit_select(rgb_counter, 1)):
                m.d.sync += self.data.eq(bit_counter > (T_PERIOD - T_ON))
            with m.Else():
                m.d.sync += self.data.eq(bit_counter > (T_PERIOD - T_OFF))

            m.d.sync += bit_counter.eq(bit_counter - 1)

            with m.If(bit_counter == 0):
                m.d.sync += [
                    bit_counter.eq(T_PERIOD),
                    rgb_counter.eq(rgb_counter - 1)
                ]

                with m.If(rgb_counter == 0):
                    m.d.sync += [
                        led_counter.eq(led_counter - 1),
                        bit_counter.eq(T_PERIOD),
                        rgb_counter.eq(23)
                    ]

                    with m.If(led_counter == 0):
                        m.d.sync += [
                            state.eq(STATE_RESET),
                            led_counter.eq(self.NUM_LEDS - 1),
                            bit_counter.eq(T_RESET)
                        ]

        return m


from nmigen import *
from nmigen_boards.blackice_mx import *

class LedGlow(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(4)]

        cnt       = Signal(26)
        pwm_input = Signal(4)
        pwm       = Signal(5)

        m = Module()

        m.d.sync += [
            cnt.eq(cnt + 1),
            pwm.eq(pwm[:-1] + pwm_input),
            pwm_input.eq(Mux(cnt[-1], cnt[-5:], ~cnt[-5:]))
        ]

        for l in led:
            m.d.comb += l.eq(pwm[-1])

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(LedGlow(), do_program=True)


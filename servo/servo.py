from nmigen import *

from nmigen.utils import bits_for

class Servo(Elaboratable):
    def __init__(self):
        # inputs
        self.on        = Signal()
        self.angle     = Signal(signed(8))

        # output
        self.out       = Signal()

    def elaborate(self, platform):

        clk_freq          = int(platform.default_clk_frequency)
        cycles_per_pulse  = int(clk_freq // 50) # 20ms
        cnt_bits          = bits_for(cycles_per_pulse)
        cycles_per_degree = C(int((cycles_per_pulse // 40) // 90), cnt_bits)
        zero_point        = C(int((cycles_per_pulse // 40) * 3), cnt_bits) # 1.5ms
        print("cycles per pulse:", cycles_per_pulse)
        print("cycles per degree:", cycles_per_degree)
        print("zero point:", zero_point)

        cnt = Signal(cnt_bits, reset=0)

        m = Module()
        
        with m.If(self.on):
            m.d.sync += cnt.eq(cnt + 1)
            with m.If(cnt == (cycles_per_pulse - 1)):
                m.d.sync += [
                    cnt.eq(0),
                    self.out.eq(1)
                ]
            with m.Elif(cnt == (zero_point + (self.angle * cycles_per_degree))):
                m.d.sync += self.out.eq(0)
        with m.Else():
            m.d.sync += self.out.eq(0)

        return m


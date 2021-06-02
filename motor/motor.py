from nmigen import *

class EncoderMotor(Elaboratable):
    def __init__(self):
        # inputs
        self.on        = Signal()
        self.reset     = Signal()
        self.dir       = Signal()
        self.power     = Signal(8)
        self.quad1     = Signal(1)
        self.quad2     = Signal(1)

        # outputs
        self.mplus     = Signal()
        self.mminus    = Signal()
        self.turns     = Signal(signed(17))

    def elaborate(self, platform):
        m = Module()

        cnt     = Signal(8)
        r_quad1 = Signal(3)
        r_quad2 = Signal(3)

        with m.If(self.reset):
            self.turns.eq(0)

        m.d.sync += [
            r_quad1.eq(Cat(self.quad1, r_quad1[:2])),
            r_quad2.eq(Cat(self.quad2, r_quad2[:2]))
        ]

        with m.If(r_quad1[2] ^ r_quad1[1] ^ r_quad2[2] ^ r_quad2[1]):
            with m.If(r_quad1[2] ^ r_quad2[1]):
                m.d.sync += self.turns.eq(self.turns + 1)
            with m.Else():
                m.d.sync += self.turns.eq(self.turns - 1)

        with m.If(self.on & (self.power > 0)):
            m.d.sync += cnt.eq(cnt + 1)
            with m.If(self.dir):
                m.d.comb += [
                    self.mplus.eq(cnt <= self.power),
                    self.mminus.eq(0)
                ]
            with m.Else():
                m.d.comb += [
                    self.mplus.eq(0),
                    self.mminus.eq(cnt <= self.power)
                ]

        return m
 

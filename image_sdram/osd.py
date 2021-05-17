from nmigen import *

class OSD(Elaboratable):
    def __init__(self, x_start=600, y_start=384, width=8, height=96):
        # parameters
        self.x_start = x_start
        self.y_start = y_start
        self.width   = width
        self.height  = height

        # inputs
        self.on      = Signal()
        self.osd_val = Signal(4)
        self.i_r     = Signal(4)
        self.i_g     = Signal(4)
        self.i_b     = Signal(4)
        self.x       = Signal(10)
        self.y       = Signal(10)
        self.sel     = Signal()

        # outputs
        self.o_r     = Signal(4)
        self.o_g     = Signal(4)
        self.o_b     = Signal(4)

    def elaborate(self, platform):
        m = Module()

        # Copy color by default
        m.d.sync += [
            self.o_r.eq(self.i_r),
            self.o_g.eq(self.i_g),
            self.o_b.eq(self.i_b)
        ]

        y_offset = Signal(10)
        xb = Signal(3)
        yb = Signal(3)

        m.d.comb += [
            y_offset.eq(self.y - self.y_start),
            xb.eq(self.x[:3]),
            yb.eq(self.y[:3])
        ]

        with m.If(self.on):
            with m.If((self.x >= self.x_start) & (self.x < self.x_start + self.width) &
                      (self.y >= self.y_start) & (self.y < self.y_start + self.height)):
                m.d.sync += [
                    self.o_r.eq(0),
                    self.o_g.eq(0),
                    self.o_b.eq(0)
                ]

                with m.If(y_offset[3:] == self.osd_val):
                    m.d.sync += [
                        self.o_r.eq(2),
                        self.o_g.eq(2),
                        self.o_b.eq(2)
                    ]

                    with m.If(self.sel & ((xb == 0) | (xb == 7) |
                                          (yb == 0) | (yb == 7))):
                        m.d.sync += [
                            self.o_r.eq(0xF),
                            self.o_g.eq(0),
                            self.o_b.eq(0)
                        ]


                    with m.Switch(self.osd_val):
                        with m.Case(0): # brightness
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0xF),
                                    self.o_g.eq(0xF),
                                    self.o_b.eq(0xF)
                                ]
                        with m.Case(1): # red
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0xF),
                                    self.o_g.eq(0),
                                    self.o_b.eq(0)
                                ]
                        with m.Case(2): # green
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0),
                                    self.o_g.eq(0xF),
                                    self.o_b.eq(0)
                                ]
                        with m.Case(3): # blue
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0),
                                    self.o_g.eq(0),
                                    self.o_b.eq(0xF)
                                ]
                        with m.Case(4): # monochrome
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(3),
                                    self.o_g.eq(3),
                                    self.o_b.eq(3)
                                ]
                        with m.Case(5): # X flip
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(Mux((xb == yb) | (xb == (7 - yb)), 0xF, 0)),
                                    self.o_g.eq(Mux((xb == yb) | (xb == (7 - yb)), 0xF, 0)),
                                    self.o_b.eq(Mux((xb == yb) | (xb == (7 - yb)), 0xF, 0))
                                ]
                        with m.Case(6): # Y flip
                            with m.If((xb > 1) & (xb < 6) &
                                      (yb > 1) & (yb < 6)):
                                m.d.sync += [
                                    self.o_r.eq(Mux((((yb == 5) & ((xb == 3) |( xb == 4)))) | ((yb != 5) & ((xb == yb) | (xb == (7 - yb)))), 0xF, 0)),
                                    self.o_g.eq(Mux((((yb == 5) & ((xb == 3) |( xb == 4)))) | ((yb != 5) & ((xb == yb) | (xb == (7 - yb)))), 0xF, 0)),
                                    self.o_b.eq(Mux((((yb == 5) & ((xb == 3) |( xb == 4)))) | ((yb != 5) & ((xb == yb) | (xb == (7 - yb)))), 0xF, 0))
                                ]
                        with m.Case(7): # Border
                            with m.If((xb == 1) | (xb == 6) |
                                      (yb == 1) | (yb == 6)):
                                m.d.sync += [
                                    self.o_r.eq(0),
                                    self.o_g.eq(0),
                                    self.o_b.eq(0xF)
                                ]

        return m


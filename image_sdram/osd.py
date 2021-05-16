from nmigen import *

class OSD(Elaboratable):
    def __init__(self, x_start=600, y_start=416, width=8, height=64):
        # parameters
        self.x_start = x_start
        self.y_start = y_start
        self.width   = width
        self.height  = height

        # inputs
        self.on      = Signal()
        self.osd_val = Signal(3)
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

        m.d.comb += y_offset.eq(self.y - self.y_start)

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

                    with m.If(self.sel & ((self.x[:3] == 0) | (self.x[:3] == 7) |
                                       (self.y[:3] == 0) | (self.y[:3] == 7))):
                        m.d.sync += [
                            self.o_r.eq(0xF),
                            self.o_g.eq(0),
                            self.o_b.eq(0)
                        ]


                    with m.Switch(self.osd_val):
                        with m.Case(0): # brightness
                            with m.If((self.x[:3] > 1) & (self.x[:3] < 6) &
                                      (self.y[:3] > 1) & (self.y[:3] < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0xF),
                                    self.o_g.eq(0xF),
                                    self.o_b.eq(0xF)
                                ]
                        with m.Case(1): # red
                            with m.If((self.x[:3] > 1) & (self.x[:3] < 6) &
                                      (self.y[:3] > 1) & (self.y[:3] < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0xF),
                                    self.o_g.eq(0),
                                    self.o_b.eq(0)
                                ]
                        with m.Case(2): # green
                            with m.If((self.x[:3] > 1) & (self.x[:3] < 6) &
                                      (self.y[:3] > 1) & (self.y[:3] < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0),
                                    self.o_g.eq(0xF),
                                    self.o_b.eq(0)
                                ]
                        with m.Case(3): # blue
                            with m.If((self.x[:3] > 1) & (self.x[:3] < 6) &
                                      (self.y[:3] > 1) & (self.y[:3] < 6)):
                                m.d.sync += [
                                    self.o_r.eq(0),
                                    self.o_g.eq(0),
                                    self.o_b.eq(0xF)
                                ]
                        with m.Case(4): # monochrome
                            with m.If((self.x[:3] > 1) & (self.x[:3] < 6) &
                                      (self.y[:3] > 1) & (self.y[:3] < 6)):
                                m.d.sync += [
                                    self.o_r.eq(3),
                                    self.o_g.eq(3),
                                    self.o_b.eq(3)
                                ]

        return m


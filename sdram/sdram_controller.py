from nmigen import Signal, Instance, Elaboratable, C
from nmigen import Module, ClockSignal, ResetSignal
from nmigen.build import Pins, Attrs
from sdram_d8 import Sdram

class sdram_controller(Elaboratable):
    def __init__(self):
        # inputs
        self.address   = Signal(21) # byte address
        self.req_read  = Signal()
        self.req_write = Signal()
        self.data_in   = Signal(8)
        self.init      = Signal()
        self.clkref    = Signal()

        # outputs
        self.data_out  = Signal(8)
    
    def elaborate(self, platform):
        m = Module()

        # Get the SDRAM pins
        dir_dict = {
            "a":"-",
            "ba":"-",
            "cke":"-",
            "clk":"-",
            "clk_en":"-",
            "dq":"-",
            "dqm":"-",
            "cas":"-",
            "cs":"-",
            "ras":"-",
            "we":"-",
            }
        
        sdram = platform.request("sdram", dir=dir_dict)

        # Create the controller
        m.submodules.ctrl = ctrl = Sdram()

        m.d.comb += [
            # Set the chip output pins
            sdram.a.eq(ctrl.sd_addr),
            sdram.dqm.eq(ctrl.sd_dqm),
            sdram.ba.eq(ctrl.sd_ba),
            sdram.cs.eq(ctrl.sd_cs),
            sdram.we.eq(ctrl.sd_we),
            sdram.ras.eq(ctrl.sd_ras),
            sdram.cas.eq(ctrl.sd_cas),
            sdram.clk_en.eq(1),
            sdram.clk.eq(ClockSignal("sdram")),
            # Set the controller input pins
            ctrl.init.eq(self.init),
            ctrl.clkref.eq(self.clkref),
            ctrl.dinA.eq(self.data_in),
            ctrl.addrA.eq(self.address),
            ctrl.weA.eq(self.req_write),
            ctrl.oeA.eq(self.req_read),
            # Set output pins
            self.data_out.eq(ctrl.doutA)
        ]

        # Set dq to input or output depending on we_out
        for i in range(16):
            dq_io = Instance("SB_IO",
                p_PIN_TYPE=C(0b101001, 6),
                p_PULLUP=C(0),
                io_PACKAGE_PIN=sdram.dq[i],
                i_OUTPUT_ENABLE=ctrl.we_out,
                i_D_OUT_0=ctrl.sd_data_out[i],
                o_D_IN_0=ctrl.sd_data_in[i],
            )

            m.submodules += dq_io
        
        return m


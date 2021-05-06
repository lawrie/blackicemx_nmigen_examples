from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *
from opc6 import *

class OPC6Test(Elaboratable):
    def elaborate(self, platform):
        led = [platform.request("led", i) for i in range(4)]
        leds = Cat([led[i].o for i in range(4)])

        opc6 = OPC6()

        m = Module()
        m.submodules.opc6 = opc6

        m.d.comb += [
            opc6.int_b.eq(3),
            opc6.reset_b.eq(1),
            opc6.clken.eq(1),
            opc6.din.eq(0x3000),
            leds.eq(opc6.dout)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(OPC6Test(), do_program=True)


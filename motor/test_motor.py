from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from motor import EncoderMotor

encoder_motor_pmod = [
    Resource("motor", 0,
            Subsignal("mplus",  Pins("7",  dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("mminus", Pins("8",  dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("quad1",  Pins("9",  dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("quad2",  Pins("10", dir="i", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Test(Elaboratable):
    def elaborate(self, platform):
        motor_pins = platform.request("motor")
        m = Module()

        m.submodules.motor = motor = EncoderMotor()

        m.d.comb += [
            motor.on.eq(1),
            motor.power.eq(128),
            motor_pins.mplus.eq(motor.mplus),
            motor_pins.mminus.eq(motor.mminus),
            motor.quad1.eq(motor_pins.quad1),
            motor.quad2.eq(motor_pins.quad2)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(encoder_motor_pmod)
    platform.build(Test(), do_program=True)

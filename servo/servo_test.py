from nmigen import *
from nmigen.build import *
from nmigen_boards.blackice_mx import *

from servo import Servo

servo_pmod= [
    Resource("servo", 0,
            Subsignal("p1", Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("p2", Pins("2", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("p3", Pins("3", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("p4", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Top(Elaboratable):
    def elaborate(self, platform):
        servo_pins = platform.request("servo")

        m = Module()

        m.submodules.servo = servo = Servo()

        m.d.comb += [
            servo.on.eq(1),
            servo_pins.p1.eq(servo.out),
            servo.angle.eq(120)
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(servo_pmod)
    platform.build(Top(), do_program=True)


from nmigen import *
from nmigen_stdio.serial import AsyncSerial
from nmigen.build import *
from nmigen_boards.blackice_mx import *

audio_pmod= [
    Resource("audio", 0,
            Subsignal("ain",      Pins("1", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")),
            Subsignal("shutdown", Pins("4", dir="o", conn=("pmod",5)), Attrs(IO_STANDARD="SB_LVCMOS")))
]

class Stream(Elaboratable):
    def elaborate(self, platform):
        audio  = platform.request("audio")
        uart    = platform.request("uart")
        divisor = int(platform.default_clk_frequency // 115200)

        m = Module()

        # Create the uart
        m.submodules.serial = serial = AsyncSerial(divisor=divisor, pins=uart)

        pwm_acc = Signal(9)
        dat_r   = Signal(8)

        m.d.comb += [
            audio.shutdown.eq(1),
            serial.rx.ack.eq(1),
            audio.ain.eq(pwm_acc[-1])
        ]

        with m.If(serial.rx.rdy):
            m.d.sync += dat_r.eq(serial.rx.data)

        m.d.sync += pwm_acc.eq(pwm_acc[:8] + dat_r)

        
        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.add_resources(audio_pmod)
    platform.build(Stream(), do_program=True)


from nmigen import *
from nmigen_stdio.serial import *

from nmigen_boards.blackice_mx import *

class UartTest(Elaboratable):
    def elaborate(self, platform):

        uart    = platform.request("uart")
        leds    = Cat([platform.request("led", i) for i in range(4)])
        divisor = int(platform.default_clk_frequency // 115200)

        m = Module()

        # Create the uart
        m.submodules.serial = serial = AsyncSerial(divisor=divisor, pins=uart)

        m.d.comb += [
            # Connect data out to data in
            serial.tx.data.eq(serial.rx.data),
            # Always allow reads
            serial.rx.ack.eq(1),
            # Write data when received
            serial.tx.ack.eq(serial.rx.rdy),
            # Show any errors on leds: red for parity, green for overflow, blue for frame
            leds.eq(Cat(serial.rx.err.frame, serial.rx.err.overflow, 0b0, serial.rx.err.parity))
        ]

        return m

if __name__ == "__main__":
    platform = BlackIceMXPlatform()
    platform.build(UartTest(), do_program=True)


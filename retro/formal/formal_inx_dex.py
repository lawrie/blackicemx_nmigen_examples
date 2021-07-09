# Copyright (C) 2020 Robert Baruch <robert.c.baruch@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from nmigen import Signal, Value, Cat, Module, Mux
from nmigen.hdl.ast import Statement
from nmigen.asserts import Assert
from .verification import FormalData, Verification

INX = "00001000"
DEX = "00001001"


class Formal(Verification):
    def __init__(self):
        super().__init__()

    def valid(self, instr: Value) -> Value:
        return instr.matches(INX, DEX)

    def check(self, m: Module):
        self.assert_cycles(m, 4)
        self.assert_cycle_signals(m, 2, vma=0, ba=0)
        self.assert_cycle_signals(m, 3, vma=0, ba=0)

        with m.If(self.instr.matches(INX)):
            self.assert_registers(m, X=self.data.pre_x + 1, PC=self.data.pre_pc + 1)
        with m.Else():
            self.assert_registers(m, X=self.data.pre_x - 1, PC=self.data.pre_pc + 1)

        self.assert_flags(m, Z=(self.data.post_x == 0))

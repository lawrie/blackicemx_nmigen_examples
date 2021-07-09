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

from enum import IntEnum


class ModeBits(IntEnum):
    """Decoding of bits 4 and 5 for instructions >= 0x80."""
    IMMEDIATE = 0
    A = 0  # An alias for instructions in 0x40-0x7F
    DIRECT = 1
    B = 1  # An alias for instructions in 0x40-0x7F
    INDEXED = 2
    EXTENDED = 3


class Flags(IntEnum):
    """Flag positions."""
    H = 5
    I = 4
    N = 3
    Z = 2
    V = 1
    C = 0

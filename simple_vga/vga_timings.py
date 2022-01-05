from typing import NamedTuple


class VGATiming(NamedTuple):
    x: int
    y: int
    refresh_rate: float
    pixel_freq: int
    h_front_porch: int
    h_sync_pulse: int
    h_back_porch: int
    v_front_porch: int
    v_sync_pulse: int
    v_back_porch: int

vga_timings = {
    '640x480@60Hz': VGATiming(
        x             = 640,
        y             = 480,
        refresh_rate  = 60.0,
        pixel_freq    = 25_175_000,
        h_front_porch = 16,
        h_sync_pulse  = 96,
        h_back_porch  = 48,
        v_front_porch = 10,
        v_sync_pulse  = 2,
        v_back_porch  = 33),
    '800x600@60Hz': VGATiming(
        x             = 800,
        y             = 600,
        refresh_rate  = 60.0,
        pixel_freq    = 40_000_000,
        h_front_porch = 40,
        h_sync_pulse  = 128,
        h_back_porch  = 88,
        v_front_porch = 1,
        v_sync_pulse  = 4,
        v_back_porch  = 23),
    '1024x768@60Hz': VGATiming(
        x             = 1024,
        y             = 768,
        refresh_rate  = 60.0,
        pixel_freq    = 65_000_000,
        h_front_porch = 24,
        h_sync_pulse  = 136,
        h_back_porch  = 160,
        v_front_porch = 3,
        v_sync_pulse  = 6,
        v_back_porch  = 29),
}

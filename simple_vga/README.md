# VGA example

```bash
python top_vgatest.py
```


# Flexible video modes
To change the video mode, change the parameter passed to the `TopVGA` class:

```python
m.submodules.top = top = TopVGATest(timing=vga_timings['1920x1080@30Hz'])
```

Check the `dvi/vga_timings.py` file for all available video modes. You can also add your own video modes to that file as well.

If you get a timing failure during the place and route (PnR) step, you could adjust the number of bits used for the horizontal and vertical counters (`bits_x` and `bits_y`) of the `VGA` class:

```python
m.submodules.vga = vga = VGA(
    resolution_x      = self.timing.x,
    hsync_front_porch = hsync_front_porch,
    hsync_pulse       = hsync_pulse_width,
    hsync_back_porch  = hsync_back_porch,
    resolution_y      = self.timing.y,
    vsync_front_porch = vsync_front_porch,
    vsync_pulse       = vsync_pulse_width,
    vsync_back_porch  = vsync_back_porch,
    bits_x            = 16, # Play around with the sizes because sometimes
    bits_y            = 16  # a smaller/larger value will make it pass timing.
)
```

Without an overclock, the maximum resolution is 1920x1080@30Hz, but some monitors will not accept 30Hz. If monitor doesn't show the correct refresh rate, then it can be fine tuned. Negative values will raise refresh rate. Positive values will lower refresh rate.

```python
xadjustf=0, # adjust -3..3 if no picture
yadjustf=0, # or to fine-tune f
```

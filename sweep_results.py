# Copyright (c) Ales Shovkoplyas VE3NEA

from helper_func import *

class SweepResults:
    def __init__(self, frequencies):
        self.frequencies = frequencies
        
        self.impedances: List(complex)
        self.reflection_coeffs: List(complex)
        self.return_losses: List(float)
        self.swrs: List(float)
        
        self.max_return_loss: float
        self.freq_of_max: float

        self.gains: List(float)
        self.front_back_ratios: List(float)

    def set_impedances(self, impedances):
        self.impedances = impedances
        self.reflection_coeffs = [z_to_reflection_coeff(z) for z in impedances]
        self.return_losses = [z_to_return_loss(z) for z in impedances]
        self.swrs = [z_to_vswr(z) for z in impedances]

        self._find_minimum()

    def _find_minimum(self):
        idx = np.argmax(self.return_losses)
        if (idx == 0 or idx == len(self.return_losses) - 1):
            self.max_return_loss = self.return_losses[idx]
            self.freq_of_max = self.frequencies[idx]
        else:
            # fit parabola to find the exact minimum            
            yl = self.return_losses[idx-1]
            y0 = self.return_losses[idx]
            yr = self.return_losses[idx+1]            
            
            a = (yr + yl) / 2 - y0
            b = (yr - yl) / 2

            x = - b / (2 * a)
            y = a * x * x + b * x + y0;
            
            step = self.frequencies[idx + 1] - self.frequencies[idx]
            self.freq_of_max = self.frequencies[idx] + x * step
            self.max_return_loss = y
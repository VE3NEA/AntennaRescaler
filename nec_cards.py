# Copyright (c) Ales Shovkoplyas VE3NEA

# Wire, Loading, Excitation, Gouund and Frequency classes
# perform two-way conversion between the NEC cards
# and parameters of the PyNEC methods

import numpy as np

class Wire:
    def __init__(self, args):
        self.tag = args[0]
        self.segment_count = args[1]
        self.p1 = np.array([args[2], args[3], args[4]])
        self.p2 = np.array([args[5], args[6], args[7]])
        self.radius = args[8]

    def params(self):
        return [self.tag, self.segment_count, self.p1[0], self.p1[1], self.p1[2], self.p2[0], self.p2[1], self.p2[2], self.radius, 1, 1]

    def card(self):
        return f"GW {self.tag} {self.segment_count} {self.p1[0]:.5f} {self.p1[1]:.5f} {self.p1[2]:.5f} {self.p2[0]:.5f} {self.p2[1]:.5f} {self.p2[2]:.5f} {self.radius:.6f}" 


class Loading:
    def __init__(self, args):
        # feel free to add support of other types
        if args[0] != 5:
            raise Exception("LD cards must be of type 5")
        self.tag = args[1]
        self.conductivity = args[4]

    def params(self):
        return[5, self.tag, 0, 0, self.conductivity, 0, 0]

    def card(self):
        return f"LD 5 {self.tag} 0 0 {self.conductivity} 0" 

class Excitation:
    def __init__(self, args):
        if args[0] in range(1, 5):
            raise Exception("EX cards must be of type 0")
        self.tag = args[1]
        self.segment = args[2]
        self.voltage = complex(args[4], args[5]) 

    def params(self):
        return[0, self.tag, self.segment, 0, self.voltage.real, self.voltage.imag, 0, 0, 0, 0]

    def card(self):
        return f"EX 0 {self.tag} {self.segment} 0 {self.voltage.real} {self.voltage.imag}" 
        
class Ground:    
    def __init__(self, args):
        if args[0] != -1:
            raise Exception("GN cards must be of type -1")
            
    def params(self):
        return[-1, 0, 0, 0, 0, 0, 0, 0]
        
    def card(self):
        return f"GN -1" 

class Frequency:
    def __init__(self, args):
        self.step_type = args[0]
        self.step_count = args[1]
        self.frequency = args[4]
        self.step_size = args[5]

    def params(self):
        return [self.step_type, self.step_count, self.frequency, self.step_size]

    def card(self):
        return f"FR {self.step_type} {self.step_count} 0 0 {self.frequency} {self.step_size}" 

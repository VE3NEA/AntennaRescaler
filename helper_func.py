# Copyright (c) Ales Shovkoplyas VE3NEA

import numpy as np

def to_db_p(x): 
    return 10 * np.log10(x)
    
def to_db_v(x): 
    return 20 * np.log10(x)

def from_db_p(x):
    return 10 ** (x / 10.0)

def from_db_v(x):
    return 10 ** (x / 20.0)

def z_to_reflection_coeff(z):
    return (z - 50) / (z + 50)

def z_to_return_loss(z):
    rc = np.abs(z_to_reflection_coeff(z))
    return -to_db_v(rc);

def z_to_vswr(z):
    rc = np.abs(z_to_reflection_coeff(z))
    return (1 + rc) / (1 - rc)

def list_frequencies(start_freq, end_freq, step):
   if step == 0:
       return [start_freq]
   else:
       count = int((end_freq - start_freq) / step) + 1;
       return np.linspace(start_freq, end_freq, count)
            
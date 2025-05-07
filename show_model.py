# Copyright (c) Ales Shovkoplyas VE3NEA

import matplotlib.pyplot as plt
import numpy as np

def db_to_arrl(db):
    return  0.89**(-db / 2)
    
def show_model(nec, sw0, sw):    
    print(f"f    = {nec.fr_cards[0].frequency} MHz")
    print(f"z    = {sw0.impedances[0]:.2f} Ohms")
    print(f"Г    = {sw0.reflection_coeffs[0]:.3f}")
    print(f"RL   = {sw0.return_losses[0]:.2f} dB")
    print(f"SWR  = {sw0.swrs[0]:.3f}")
    print(f"gain = {sw0.gains[0]:.2f} dB")
    print(f"F/B  = {sw0.front_back_ratios[0]:.2f} dB")
    print (f"Max. RL = {sw.max_return_loss:.2f} dB at {sw.freq_of_max:.2f} MHz")

    fig = plt.figure(figsize=(9, 12))
    
    plt.subplot(311)
    plt.axvline(x = nec.fr_cards[0].frequency, color = 'g', linewidth=1)
    plt.plot(sw.frequencies, [-rl for rl in sw.return_losses], 'bo-', ms=5, label="return loss")
    plt.plot([sw.freq_of_max], [-sw.max_return_loss], 'ro', ms=5, label="max. RL")
    plt.grid(True)
    
    plt.subplot(312)
    plt.axvline(x = nec.fr_cards[0].frequency, color = 'g', linewidth=1)
    plt.plot(sw.frequencies, sw.swrs, 'mo-', ms=5, label="S.W.R.")
    plt.grid(True)
    
    plt.subplot(313)
    plt.axvline(x = nec.fr_cards[0].frequency, color = 'g', linewidth=1)
    plt.plot(sw.frequencies, sw.front_back_ratios, 'go-', ms=5, label="F/B ratio")
    plt.plot(sw.frequencies, sw.gains, 'ro-', ms=5, label="gain")
    plt.grid(True)

    fig.legend()

    # pattern
    nec.build_model()
    h_pattern = nec.compute_horizontal_pattern()
    nec.build_model()
    v_pattern = nec.compute_vertical_pattern()
    
    h_pattern[1] = db_to_arrl(h_pattern[1] - h_pattern[1][0])
    v_pattern[1] = db_to_arrl(v_pattern[1] - v_pattern[1][0])
    
    ticks = np.array([0, -3, -6, -10, -15, -20, -30, -40, -50])
    labels = ["" if t == -40 else f"{t}" for t in ticks]    
    fig = plt.figure(figsize=(6, 6))
    fig.ax = plt.subplot(111, polar=True)
    fig.ax.set_rlim(0.01, 1)
    fig.ax.set_yticks(db_to_arrl(ticks))
    fig.ax.set_yticklabels(labels)
    
    fig.ax.plot(*v_pattern, label="Vertical Pattern")
    fig.ax.plot(*h_pattern, label="Horizontal Pattern")
    fig.ax.legend(loc='lower center')
    plt.show()

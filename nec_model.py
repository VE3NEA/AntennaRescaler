# Copyright (c) Ales Shovkoplyas VE3NEA

from PyNEC import *
import scipy.optimize 
import numpy as np
import scipy
import copy

from nec_cards import *
from sweep_results import *

class NecModel:
    def __init__(self):
        self._clear_cards()

    def _clear_cards(self):
        self.cm_cards = []
        self.gw_cards = []  
        self.ld_cards = []
        self.ex_cards = []
        self.gn_cards = []
        self.fr_cards = []

    def load_from_file(self, file_path):
        self._clear_cards()
        
        with open(file_path, 'r') as file:
            text = file.read()
        self.from_text(text)

    def save_to_file(self, file_path):
        with open(file_path, 'w') as file:
            file.write(self.to_text())    

    def from_text(self, text):
        for line in text.split("\n"):
            # line = line.strip()
            card_type = line[:2].upper()
            content = line[2:].strip()
            args = self._parse_args(content)
            
            if card_type == 'CM':
                self.cm_cards.append(content)
            elif card_type == 'GW':
                self.gw_cards.append(Wire(args))
            elif card_type == 'LD':
                self.ld_cards.append(Loading(args))
            elif card_type == 'EX':
                self.ex_cards.append(Excitation(args))
            elif card_type == 'GN':
                self.gn_cards.append(Ground(args))
            elif card_type == 'FR':
                self.fr_cards.append(Frequency(args))

    def to_text(self):
        cards = []

        if len(self.cm_cards) > 0:
            for cm in self.cm_cards:
                cards.append(f"CM {cm}")
            cards.append("CE")

        for gw in self.gw_cards:
            cards.append(gw.card())
        cards.append("GE")

        for ld in self.ld_cards:
            cards.append(ld.card())
            
        for ex in self.ex_cards:
            cards.append(ex.card())
            
        for gn in self.gn_cards:
            cards.append(gn.card())

        for fr in self.fr_cards:
            cards.append(fr.card())

        return "\n".join(cards)

    def _parse_args(self, content):
        values = content.split()
        parsed_values = []

        for value in values:
            try:
                parsed_values.append(int(value))
            except ValueError:
                try:
                    parsed_values.append(float(value))
                except ValueError:
                    parsed_values.append(value)

        return parsed_values

    def build_model(self):
        self.model = nec_context()
        
        geom = self.model.get_geometry()
        for gw in self.gw_cards:
            geom.wire(*gw.params())
        self.model.geometry_complete(0)

        for ld in self.ld_cards:
            self.model.ld_card(*ld.params())
            
        for ex in self.ex_cards:
            self.model.ex_card(*ex.params())
            
        for gn in self.gn_cards:
            self.model.gn_card(*gn.params())

        for fr in self.fr_cards:
            self.model.fr_card(*fr.params())

    def compute_vertical_pattern(self, freq_index=0, azimuth=0):
        #                   0  nTheta(90-el)  nPhi(az)   1  0  0  0   Theta0  Phi0  dTheta  dPhi  1  1
        self.model.rp_card( 0, 91,            1,         1, 0, 0, 0,  90,     0,    -4,     4,    1, 1)
        rp = self.model.get_radiation_pattern(0)
        gains_db = rp.get_gain()[:,0]
        angles = (90 - rp.get_theta_angles()) * 3.1415 / 180.0
        return [angles, gains_db]
    
    def compute_horizontal_pattern(self, freq_index=0, elevation=0):
        self.model.rp_card( 0, 1,             91,        1, 0, 0, 0, 90,     0,    4,      4,   1, 1)
        rp = self.model.get_radiation_pattern(0)
        gains_db = rp.get_gain()[0]
        phis = rp.get_phi_angles() * 3.1415 / 180.0
        return [phis, gains_db]

    def sweep_frequency(self, start_freq, end_freq, step, forward_theta=90, forward_phi=0):
        sweep = SweepResults(start_freq, end_freq, step)
        old_fr_cards = self.fr_cards

        # impedance
        impedances = []

        for freq in sweep.frequencies:            
            self.fr_cards = [Frequency([0, 1, 0, 0, freq, 0])]
            self.build_model()
            self.model.xq_card(0)
            ipt = self.model.get_input_parameters(0)
            impedances.append(ipt.get_impedance()[0])                             
        sweep.set_impedances(impedances)

        sweep.gains = []
        sweep.front_back_ratios = []
        for freq in sweep.frequencies:            
            self.fr_cards = [Frequency([0, 1, 0, 0, freq, 0])]
            self.build_model()
            self.model.rp_card( 0, 1, 2, 1, 0, 0, 0, forward_theta, forward_phi, 0, 180, 1, 1)
            rp = self.model.get_radiation_pattern(0)
            gains_db = rp.get_gain()[0]
            sweep.gains.append(gains_db[0])
            sweep.front_back_ratios.append(gains_db[0] - gains_db[1])        
        
        self.fr_cards = old_fr_cards
        return sweep

    # like sweep_frequency, but on the design frequency
    def compute_characteristics(self):
        return self.sweep_frequency(self.fr_cards[0].frequency, 0, 0)

    def rescale_frequency(self, from_freq, to_freq):
        scale = from_freq / to_freq
        for sw in self.gw_cards:
            sw.p1 *= scale
            sw.p2 *= scale
            sw.radius *= scale
        self.fr_cards[0].frequency = to_freq

    def rescale_radius(self, from_radius, to_radius):
        sw0 = self.compute_characteristics()        
        
        for gw in reversed(self.gw_cards):
            if gw.radius == from_radius:
                gw.radius = to_radius                

                x0 = np.array([1])
                gw0 = copy.copy(gw)
                res = scipy.optimize.minimize(
                    self._optimization_target_function, x0, method='nelder-mead', 
                    args=(sw0, gw0, gw), options={'xatol': 1e-8, 'maxfev': 6000})


    def _optimization_target_function(self, params, sw0, gw0, gw):
        # scale all coords relative to element center 
        center = (gw0.p1 + gw0.p2) / 2
        scale = params[0]
        gw.p1 = center + scale * (gw0.p1 - center)
        gw.p2 = center + scale * (gw0.p2 - center)

        # compute antenna characteristics
        self.build_model()
        sw = self.compute_characteristics()

        # compute error
        # errors = [np.abs(sw.return_losses[0] - sw0.return_losses[0]),
        #           np.abs(sw.front_back_ratios[0] - sw0.front_back_ratios[0])]
        errors = [sw0.return_losses[0] - sw.return_losses[0],                  
                  sw0.front_back_ratios[0] - sw.front_back_ratios[0],                                              
                  sw0.gains[0] - sw.gains[0]]

        return errors[0] * 0.5 + errors[1] * 0.3 + errors[2] * 2
      
    
            
    def __repr__(self):
        return f"<NECParser: {len(self.cm_cards)} CM cards, {len(self.gw_cards)} GW wires, {len(self.ld_cards)} LD cards, " \
               f"{len(self.ex_cards)} EX cards, {len(self.gn_cards)} GN cards, {len(self.fr_cards)} FR cards>"
        
# def json_serializable(obj):
# if isinstance(obj, complex): return obj.__str__()

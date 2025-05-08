# Copyright (c) Ales Shovkoplyas VE3NEA

import copy
from PyNEC import *
import numpy as np
import scipy
import scipy.optimize 

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

    def compute_vertical_pattern(self, azimuth=0):
        #                   0  nTheta(90-el)  nPhi(az)   1  0  0  0   Theta0  Phi0  dTheta  dPhi  1  1
        self.model.rp_card( 0, 361,            1,         1, 0, 0, 0,  90,     0,    -1,     1,    1, 1)
        rp = self.model.get_radiation_pattern(0)
        gains_db = rp.get_gain()[:,0]
        angles = (90 - rp.get_theta_angles()) * 3.1415 / 180.0
        return [angles, gains_db]
    
    def compute_horizontal_pattern(self, elevation=0):
        self.model.rp_card( 0, 1,             361,        1, 0, 0, 0, 90,     0,    1,      1,   1, 1)
        rp = self.model.get_radiation_pattern(0)
        gains_db = rp.get_gain()[0]
        angles = rp.get_phi_angles() * 3.1415 / 180.0
        return [angles, gains_db]

    def sweep_frequency(self, frequencies, forward_theta=90, forward_phi=0):
        sweep = SweepResults(frequencies)
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
        frequencies = list_frequencies(self.fr_cards[0].frequency, 0, 0)
        return self.sweep_frequency(frequencies)

    def rescale_frequency(self, from_freq, to_freq):
        scale = from_freq / to_freq
        for gw in self.gw_cards:
            gw.p1 *= scale
            gw.p2 *= scale
            gw.radius *= scale
        self.fr_cards[0].frequency = to_freq

    def rescale_radius(self, from_radius, to_radius):
        original_characteristics = self.compute_characteristics()        
        
        for wire in reversed(self.gw_cards):
            if wire.radius == from_radius:
                wire.radius = to_radius                

                original_wire = copy.copy(wire)
                original_params = np.array([1]) # element length scaling factor
                
                res = scipy.optimize.minimize(
                    self._optimization_target_function, original_params, method='nelder-mead', 
                    args=(original_characteristics, original_wire, wire), options={'xatol': 1e-4, 'maxfev': 600})


    def _optimization_target_function(self, params, original_characteristics, original_wire, wire):
        # scale all coords relative to element center 
        center = (original_wire.p1 + original_wire.p2) / 2
        scale = params[0]
        wire.p1 = center + scale * (original_wire.p1 - center)
        wire.p2 = center + scale * (original_wire.p2 - center)

        # compute antenna characteristics
        self.build_model()
        characteristics = self.compute_characteristics()

        errors = [original_characteristics.return_losses[0] - characteristics.return_losses[0],                  
                  original_characteristics.front_back_ratios[0] - characteristics.front_back_ratios[0],                                             
                  original_characteristics.gains[0] - characteristics.gains[0]]

        return errors[0] * 0.5 + errors[1] * 0.3 + errors[2] * 2
      
            
    def __repr__(self):
        return f"<NECParser: {len(self.cm_cards)} CM cards, {len(self.gw_cards)} GW wires, {len(self.ld_cards)} LD cards, " \
               f"{len(self.ex_cards)} EX cards, {len(self.gn_cards)} GN cards, {len(self.fr_cards)} FR cards>"

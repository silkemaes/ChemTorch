'''
Python code to calculate the reaction rates per reaction type:
- Two-body reaction (Arrhenius law)
- CP = direct cosmic ray ionisation
- CR = cosmic ray-induced photoreaction
- Photodissociation

Written by Silke Maes, May 2023
'''

import numpy as np
from numba   import njit

from pathlib import Path

import sys


## Rate file handling

reaction_type = {'AD'  : 'AD (associative detachment)',
                 'CD'  : 'CD (collisional dissociation)',
                 'CE'  : 'CE (charge exchange)',
                 'CP'  : 'CP = CRP (cosmic-ray proton)',
                 'CR'  : 'CR = CRPHOT (cosmic-ray photon)',
                 'DR'  : 'DR (dissociative recombination)',
                 'IN'  : 'IN (ion-neutral)',
                 'MN'  : 'MN (mutual neutralisation)',
                 'NN'  : 'NN (neutral-neutral)',
                 'PH'  : 'PH (photoprocess)',
                 'RA'  : 'RA (radiative association)',
                 'REA' : 'REA (radiative electron attachement)',
                 'RR'  : 'RR (radiative rec ombination)',
                 'IP'  : 'IP (internal photon)',
                 'AP'  : 'AP (accompaning photon)'
}



## For numbers for faster calculation
frac = 1/300.
w = 0.5             ## grain albedo
alb = 1./(1.-w)


## Reading rate & species file


def read_rate_file(rate):
    '''
    Read rates file (Rate12, UMIST database, including IP, AP, HNR - reactions) \ 
    (McElroy et al., 2013, M. VdS' papers)
    '''

    loc = (Path(__file__).parent / f'../rates/rate{rate}.rates').resolve()

    rates = dict()
    with open(loc, 'r') as f:
        lines = f.readlines()
        for i in range(len(lines)):
            line = lines[i].split(':')
            rates[int(line[0])] = line[1:]
    
    type = list()
    α = np.zeros(len(rates))
    β = np.zeros(len(rates))
    γ = np.zeros(len(rates))
    for nb in rates:
        type.append(str(rates[nb][0]))
        α[nb-1] = float(rates[nb][8])
        β[nb-1] = float(rates[nb][9])
        γ[nb-1] = float(rates[nb][10])

    return rates, type, α, β, γ


def read_specs_file(chemtype, rate):
    '''
    Read species file (Rate12, UMIST database) \n 
    (McElroy et al., 2013)\n
    '''   
    
    loc_parnt = (Path(__file__).parent / f'../rates/{chemtype}.parents').resolve()
    loc_specs = (Path(__file__).parent / f'../rates/rate{rate}.specs').resolve()
    
    idxs        = np.loadtxt(loc_specs, usecols=(0), dtype=int, skiprows = 1)     
    specs_all   = np.loadtxt(loc_specs, usecols=(1), dtype=str, skiprows = 1)  ## Y in fortran77 code

    specs = list()
    convs = list()
    for i in range(len(idxs)):
        idx = idxs[i]
        if idx == 0:
            convs.append(specs_all[i])
            # print('consv', i, idx, specs_all[i])
        else:
            specs.append(specs_all[i])
            # print('non-consv', i, idx, specs_all[i])

    parnt = np.loadtxt(loc_parnt, skiprows=0   , usecols= (0,1), dtype=str)
    
    return np.array(specs), parnt.T, np.array(convs)



## Setting initial abundances
def initialise_abs(chemtype, rate):
    '''
    This function sets the initial abundance of the species: 

    INPUT:
        chemtype = chemistry type: 'C' of 'O'

    RETURN:
        - abs       = abundances of non-conserved species 
        - abs_consv = abundances of conserved species 
        - specs     = array with species names 
        (The order of specs corresponds to the order of abs)
    '''
    specs, parnt, consv = read_specs_file(chemtype, rate)

    ## Initial abundances of the non-conserved species
    abs = np.zeros(len(specs),dtype=np.float64)

    for i in range(len(specs)):
        for j in range(parnt.shape[1]):
            if specs[i] == parnt[0][j]:
                abs[i] = parnt[1][j]

        # if specs[i] == 'CO'
        #     iCO = i

    ## Initialise abundances of the conserved species
    abs_consv = np.zeros(len(consv))
    abs_consv[1] = 0.5                  ## H2

    return abs, abs_consv, specs


## Calculating the reaction rates

def calculate_rates(T, δ, Av, rate):
    '''
    Calculate the reaction rate for all reactions.

    First read in reaction rate file, from this, depending on the reaction type, \ 
    the correct reaction rate is calculated.
    '''

    rates, type, α, β, γ = read_rate_file(rate)

    k = np.zeros(len(type))

    for i in range(len(type)):
        if type[i] == 'CP':
            k[i] = CP_rate(α[i]) 
        elif type[i] == 'CR':
            k[i] = CR_rate(α[i], β[i], γ[i], T)
        elif type[i] == 'PH':
            k[i] = photodissociation_rate(α[i], γ[i], δ, Av)
        elif type[i] == 'IP':
            k[i] = 0
        elif type[i] == 'AP':
            k[i] = 0
        else:
            k[i] = Arrhenius_rate(α[i], β[i], γ[i], T)

    return k



## Rate equations

@njit
def Arrhenius_rate(α, β, γ, T):
    '''
    Arrhenius law for two-body reactions.

    Reaction-dependent parameters:
        - α = speed/probability of reaction
        - β = temperature dependence
        - γ = energy barrier

    Physics dependent parameters:
        - T = temperature

    Constants:
        - frac = 1/300
    '''
    k = α*(T*frac)**β*np.exp(-γ/T)
    return k


@njit
def CP_rate(α):
    '''
    Direct cosmic ray ionisation reaction rate, give by alpha.

    For the following reaction type: CP
    '''
    k = α
    return k


@njit
def CR_rate(α, β, γ, T):
    '''
    Cosmic ray-induced photoreaction rate.

    Reaction-dependent parameters:
        - α = speed/probability of reaction
        - β = temperature dependence
        - γ 
        
    Physics dependent parameters:
        - T = temperature
        - w = dust-grain albedo == 0.5

    Constants:
        - frac = 1/300
        - alb = 1./(1.-w)

    For the following reaction type: CR
    '''
    k = α * (T*frac)**β * (γ)*alb
    return k


@njit
def photodissociation_rate(α, γ, δ, Av):
    '''
    For the following reaction type: PH

    Photodissociation reaction rate:
        - α = speed/probability of reaction
        - γ

    Physical parameters (input model):
        - δ = outward dilution of the radiation field
        - Av = species-specific extinction (connected to optical depth)
    '''
    k = α * δ * np.exp(-γ * Av)
    return k



def read_COshielding(loc):
    '''
    Read CO photodissociation shielding rate from table (Visser et al. 2009)
    '''
    shielding = np.loadtxt(loc, skiprows=9, dtype=np.float64)
    leg = './shielding/CO/legend.txt'

    CO = np.loadtxt(leg, skiprows = 3, dtype = np.float64, usecols = (0))
    H2 = np.loadtxt(leg, skiprows = 3, dtype = np.float64, usecols = (1), max_rows=shielding.shape[0])

    return shielding, CO, H2


def retrieve_COshielding(N_CO, N_H2, shielding, CO, H2):
    '''
    Retrieve appropriate CO shielding rate
    '''
    idx, = np.where(CO ==  N_CO)
    idx_CO = idx[0]
    idx, = np.where(H2 ==  N_H2)
    idx_H2 = idx[0]
    
    shieldrate = shielding[idx_H2, idx_CO]

    return shieldrate
    
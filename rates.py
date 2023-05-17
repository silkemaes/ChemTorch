'''
Python code to calculate the reaction rates per reaction type:
- Two-body reaction (Arrhenius law)
- CP = direct cosmic ray ionisation
- CR = cosmic ray-induced photoreaction
- photodissociation

Written by Silke Maes, May 2023
'''

import numpy as np
from numba import njit


## Rate file handling

reaction_type = {'AD'  : 'AD (associative detachment)',
                 'CD'  : 'CD (collisional dissociation)',
                 'CE'  : 'CE (charge exchange)',
                 'CP'  : 'CP = CRP(cosmic-ray proton)',
                 'CR'  : 'CR = CRPHOT(cosmic-ray photon)',
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
w = 0.5         ## grain albedo
alb = 1./(1.-w)


## Reading rate & species file

'''
Read rates file (Rate12, UMIST database, including IP, AP, HNR - reactions) 
(McElroy et al., 2013, M. VdS' papers)
'''
def read_rate_file():

    loc = 'rates/rate16_IP_2330K_AP_6000K.rates'

    rates = dict()
    with open(loc, 'r') as f:
        lines = f.readlines()
        for i in range(len(lines)):
            line = lines[i].split(':')
            rates[int(line[0])] = line[1:]
    
    type = list()
    α = list()
    β = list()
    γ = list()
    for rate in rates:
        type.append((rates[rate][0]))
        α.append(float(rates[rate][8]))
        β.append(float(rates[rate][9]))
        γ.append(float(rates[rate][10]))

    return rates, type, np.array(α), np.array(β), np.array(γ)

'''
Read species file (Rate12, UMIST database)
(McElroy et al., 2013)
'''
def read_specs_file(chemtype):

    loc = 'rates/rate16_IP_6000K_'+chemtype+'rich_mean_Htot.specs'

    specs = np.loadtxt(loc, skiprows=1,   max_rows=466, usecols=(1), dtype=str)     ## Y in fortran77 code
    consv = np.loadtxt(loc, skiprows=468, max_rows=2  , usecols=(1), dtype=str)     ## X in fortran77 code
    parnt = np.loadtxt(loc, skiprows=471   , usecols= (0,1), dtype=str)
    
    return specs, parnt, consv



## Setting initial abundances

def initialise_abs(chemtype):
    specs, parnt, consv = read_specs_file(chemtype)

    Y = np.zeros(len(specs))

    for i in range(len(specs)):
        for j in range(len(parnt)):
            if specs[i] == parnt[j]:
                Y[i] = consv[j]

    return Y


def calculating_rates(T, δ, Av, w):

    rates, type, α, β, γ = read_rate_file()

    K = np.zeros(len(type))

    return K



## Rate equations

'''
Arrhenius law for two-body reactions.
Reaction-dependent parameters:
    - α = speed/probability of reaction
    - β = temperature dependence
    - γ = energy barrier
Physics dependent parameters:
    - T = temperature

For the following reaction types:
    - 

'''
@njit
def Arrhenius_rate(α, β, γ, T):
    k = α*(T*frac)**β*np.exp(-γ/T)
    return k

'''
Direct cosmic ray ionisation reaction rate, give by alpha.

For the following reaction type: CP
'''
@njit
def CP_rate(α):
    k = α
    return k

'''
Cosmic ray-induced photoreaction rate.
Reaction-dependent parameters:
    - α = speed/probability of reaction
    - β = temperature dependence
    - γ 
Physics dependent parameters:
    - T = temperature
    - w = dust-grain albedo

For the following reaction type: CR
'''
@njit
def CR_rate(α, β, γ, T, w):
    k = α * (T*frac)**β * (γ)*alb
    return k

'''
Photodissociation reaction rate.
    - α = speed/probability of reaction
    - γ
Physical parameters:
    - δ = overall dilution of the radiation field
    - Av = species-specific extinction (connected to optical depth)

For the following reaction type: PH
'''
@njit
def photodissociation_rate(α, γ, δ, Av):
    k = α * δ * np.exp(-γ * Av)
    return k


    
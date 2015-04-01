# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 10:51:55 2015

@author: Vladimir Putin
"""

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

import xrt.backends.raycing as raycing
import xrt.backends.raycing.sources as rs
#import xrt.backends.raycing.apertures as ra
import xrt.backends.raycing.oes as roe
import xrt.backends.raycing.run as rr
import xrt.backends.raycing.materials as rm
import xrt.plotter as xrtp
import xrt.runner as xrtr
import xrt.backends.raycing.screens as rsc

# see XYCAxis constructor:
#from xrt.backends import raycing

# for saving into .mat file
import scipy.io

mGlass = rm.Material(('Si', 'O'), quantities=(1, 2), rho=2.2)

repeats = 6*1500 # number of ray traycing iterations
E0 = 9000.
rSample = 10000 # starting position of the lens
f = rSample + 350. # y length in mm from foucs to the end of the lens
screen1_pos = rSample + 200
screen2_pos = f + 120
max_plots = 0
r0 = 0.03
rOut = 0.03
wall = 0.02
plot2D_yLim = [-0.05, 0.05]
plot_main_lim = 0.45 # min 2*r0 for capillary entrance imaging
layers = 10 # number of hexagonal layers
nRefl = 4 # number of reflections
nReflDisp = 12 # unused
xzPrimeMax = 3.
# Pickle saving: None for no saving
persistentName=None#'phase_space__energy.pickle'

class StraightCapillary(roe.OE):
    def __init__(self, *args, **kwargs):
        self.rSample = kwargs.pop('rSample')
        self.entranceAlpha = kwargs.pop('entranceAlpha')
        self.f = kwargs.pop('f') # 
        self.r0in = kwargs.pop('rIn')
        self.r0out = kwargs.pop('rOut')
        roe.OE.__init__(self, *args, **kwargs)

        s0 = self.f - self.rSample * np.cos(self.entranceAlpha)
        self.a0 = -np.tan(self.entranceAlpha) / 2 / s0
        self.b0 = 0.5*self.rSample * np.sin(self.entranceAlpha) - self.a0 * s0**2
        self.b0 = 0.
        self.s0 = s0
        self.ar = (self.r0out-self.r0in) / s0
        self.br = self.r0in
        self.isParametric = True

    def local_x0(self, s):  # axis of capillary, x(s)
        return 0*self.a0 * (s-0)**2 + self.b0
#        return 0.0005*np.sin(s*2*np.pi) + self.b0

    def local_x0Prime(self, s):
        return 2 * self.a0 * s * 0
#        return 0.0005*np.cos(s*2*np.pi)*2*np.pi

    def local_r0(self, s):  # radius of capillary (s)
#        return self.ar * (s-self.s0)**2 + self.br
        return -self.ar *(s-self.s0) + self.br

    def local_r0Prime(self, s):
#        return self.ar * 2 * (s-self.s0)
        return -self.ar

    def local_r(self, s, phi):
        den = np.cos(np.arctan(self.local_x0Prime(s)))**2
        return self.local_r0(s) / (np.cos(phi)**2/den + np.sin(phi)**2)

    def local_n(self, s, phi):
        a = -np.sin(phi)
        b = -np.sin(phi)*self.local_x0Prime(s) - self.local_r0Prime(s)
        c = -np.cos(phi)
        norm = np.sqrt(a**2 + b**2 + c**2)
        return a/norm, b/norm, c/norm

    def xyz_to_param(self, x, y, z):
        """ *s*, *r*, *phi* are cynindrc-like coordinates of the capillary.
        *s* is along y in inverse direction, started at the exit,
        *r* is measured from the capillary axis x0(s)
        *phi* is the polar angle measured from the z (vertical) direction."""
        s = self.f - y
        phi = np.arctan2(x - self.local_x0(s), z)
        r = np.sqrt((x-self.local_x0(s))**2 + z**2)
        return s, phi, r

    def param_to_xyz(self, s, phi, r):
        x = self.local_x0(s) + r*np.sin(phi)
        y = self.f - s
        z = r * np.cos(phi)
        return x, y, z
        
def build_beamline(nrays=1000):
    beamLine = raycing.BeamLine(height=0)
    rs.GeometricSource(
        beamLine, 'GeometricSource', (0,0,0), nrays=nrays,
        dx=0.01, dz=0.1, distxprime='annulus',
        distE='normal', energies=(E0,20), polarization='horizontal')        
    # yo    
    beamLine.fsm1 = rsc.Screen(beamLine, 'DiamondFSM1', (0,screen1_pos,0))
    
    # try to remove superflous container
    #beamLine.capillaries = []
    beamLine.xzMax = 0 # no ide what this does
    # this parameter should be @line 8
    alpha = 0.0005 # hopefully milliradian
    roll = 0 # test if this rotates whole object
    capillary = StraightCapillary(
        beamLine, 'StraightCapillary', [0,0,0], roll=roll,
        material=mGlass, limPhysY=[rSample*np.cos(alpha), f],
        order=8, f=f, rSample=rSample, entranceAlpha=alpha, rIn=r0, rOut=rOut)
    beamLine.capillary = capillary         
#    beamLine.capillaries.append(capillary)         
    
    if beamLine.xzMax < capillary.b0:
        beamLine.xzMax = capillary.b0
    beamLine.xzMax += 2*r0
    
    n=1     # one layer..
    beamLine.sources[0].dxprime = 0, np.arcsin((2*n+1) * (r0+wall) / rSample)
    beamLine.fsm2 = rsc.Screen(beamLine,'DiamondFSM2', (0,screen2_pos,0))
    beamLine.myFsms = []
    for it in range(0,max_plots):
        beamLine.myFsms.append(rsc.Screen(beamLine,'myScreen{0:02d}'.format(it),(0,rSample+145*it,0)))

    return beamLine
         
def run_process(beamLine, shineOnly1stSource=False):
    beamSource = beamLine.sources[0].shine()
    # at the entrance
    beamFSM1 = beamLine.fsm1.expose(beamSource)
    outDict = {'beamSource': beamSource, 'beamFSM1': beamFSM1}
    beamCapillaryGlobalTotal = None
    capillary = beamLine.capillary
    beamCapillaryGlobal, beamCapillaryLocalN =\
        capillary.multiple_reflect(beamSource, maxReflections=nRefl)
    beamCapillaryLocalN.phi /= np.pi
    if beamCapillaryGlobalTotal is None:
        beamCapillaryGlobalTotal = beamCapillaryGlobal 
    else:
        good = ((beamCapillaryGlobal.state == 1) |
                (beamCapillaryGlobal.state == 3))
        rs.copy_beam(beamCapillaryGlobalTotal, beamCapillaryGlobal,
                     good, includeState=True)
    outDict['myBeam_after_local'] = beamCapillaryLocalN
    outDict['myBeam_after_global'] = beamCapillaryGlobalTotal

    # Create second screen
    beamFSM2 = beamLine.fsm2.expose(beamCapillaryGlobalTotal)
    outDict['beamFSM2'] = beamFSM2
    beamFsms = []
    for it in range(0,max_plots):
        beamFsms.append(beamLine.myFsms[it].expose(beamCapillaryGlobalTotal))
        outDict['myExposedScreen{0:02d}'.format(it)] = beamFsms[it]
    return outDict
rr.run_process = run_process  


def main():
    beamLine = build_beamline()
    plots = []

    xLimits = [-0.065, 0.065]
    yLimits = [-0.005, 0.005]
#    yLimits=None
    cLimits = [8900,9100]
    # at the entrance
    plot = xrtp.XYCPlot('beamFSM2', (1,3),
        xaxis=xrtp.XYCAxis(r"$x$", 'mm', data=raycing.get_x, bins=256, ppb=2, limits=xLimits),
        yaxis=xrtp.XYCAxis(r"$x'$", 'mrad', data=raycing.get_xprime, bins=256, ppb=2, limits=yLimits),
#        caxis='category', 
        caxis=xrtp.XYCAxis("Reflections", 'num. of',data=raycing.get_reflection_number, bins=256, ppb=2, limits=[0,7]),
        beamState='beamFSM2', title='FSM2_Cat', aspect='auto',
        persistentName=persistentName)
    # setting persistentName saves data into a python pickle, and might be
    # unhealthy if pickle isn't cleared/deleted when plotted data changes
    plot.baseName = 'phaseSearch'
    plot.saveName = plot.baseName + '.png'
    plots.append(plot)
#    for it in range(0,max_plots):
#        plot = xrtp.XYCPlot('myExposedScreen{0:02d}'.format(it), (1,3),
#            xaxis=xrtp.XYCAxis(r'$x$', 'mm', bins=256, ppb=2, limits=limits1),
#            yaxis=xrtp.XYCAxis(r'$z$', 'mm', bins=256, ppb=2, limits=limits1),
#            caxis='category', beamState='myExposedScreen{0:02d}'.format(it), title=str(it))
#        plot.baseName = 'inside_one_capillary_multiple_screens' + str(100+it)
#        plot.saveName = plot.baseName + '.png'
#        plots.append(plot)
    xrtr.run_ray_tracing(plots, repeats=repeats, beamLine=beamLine, processes=1)
    
    # savemat() takes a dict of names later loaded into matlab and objects
    # we want to save,
    scipy.io.savemat('xrt_data.mat',{'total2D_RGB':plot.total2D_RGB,
                                 'total2D':plot.total2D,
                                 'caxis_total':plot.caxis.total1D,
                                 'caxis_total_RGB':plot.caxis.total1D_RGB})
    # just for debug 
    return plot                                 
    
    
if __name__ == '__main__':
#    plot2D()    
    main()
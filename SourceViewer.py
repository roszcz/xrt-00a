# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 12:45:42 2015

@author: Igor Stravinski
"""

import numpy as np

import xrt.backends.raycing as raycing
import xrt.backends.raycing.sources as rs
#import xrt.backends.raycing.apertures as ra
import xrt.backends.raycing.oes as roe
import xrt.backends.raycing.run as rr
import xrt.backends.raycing.materials as rm
import xrt.plotter as xrtp
import xrt.runner as xrtr
import xrt.backends.raycing.screens as rsc

""" WELL DOCUMENTED PARAMETERS """
repeats = 1e4   # liczba
E0      = 9000  # [eV]
min_d   = 0     # [mm] | source - screen distance
step    = 10    # [mm] | screen step size
N_      = 5     # number of step to take

xLimits = [-6.05, 6.05] # Plot limits
zLimits = xLimits       # axis square

processes = 8

""" GeometricSource():: PARAMETERS TO CHECK: """
bl_height   = 0.
bl_xzMax    = 0.

# x-direction parameters
distx       = 'flat'
dx          = 0.1
distxprime  = 'flat'
dxprime     = 0.1
# z-direction
distz       = 'flat'
dz          = 0.1
distzprime  = 'flat'
dzprime     = 0.1

def build_beamline(nrays=1000):
    beamLine = raycing.BeamLine(height=bl_height)
    
    # source appends itself to the provided beamline
    rs.GeometricSource(
        beamLine,'GeometricSource',(0,0,0), nrays=nrays,
        distx=distx, dx=dx, distxprime=distxprime, dxprime=dxprime,
        distz=distz, dz=dz, distzprime=distzprime, dzprime=dzprime,
        distE='lines', energies=(E0,), polarization='horizontal')
        
    # some mysterious parameters
    beamLine.xzMax = bl_xzMax
        
    # prepare container for multiple screens
    beamLine.myScreens = []
    for it in range(0,N_):
        c_dist = min_d + it * step
        beamLine.myScreens.append(rsc.Screen(beamLine,
                                             'd = {0:02d}'.format(it),
                                            (0,c_dist,0)))
                                            
    return beamLine
    
def run_process(beamLine, shineOnly1stSource=False):
    beamSource = beamLine.sources[0].shine()
    
    # prepare empty python - dictionary for screens
    outDict = {}
    # and for beames?
    outBeams = []
    
    for it in range(0,N_):
        outBeams.append(beamLine.myScreens[it].expose(beamSource))
        outDict['screen_{0:02d}'.format(it)] = outBeams[it]
        
    return outDict
rr.run_process = run_process

def main():
    beamLine = build_beamline()
    plots = []

    
    for it in range(0,N_):
        c_dist = min_d + it * step
        plot = xrtp.XYCPlot('screen_{0:02d}'.format(it),(1,3),
            xaxis=xrtp.XYCAxis(r'$x$', 'mm', bins=256, ppb=2, limits=xLimits),
            yaxis=xrtp.XYCAxis(r'$z$', 'mm', bins=256, ppb=2, limits=zLimits),
            caxis='category', beamState='screen_{0:02d}'.format(it),
            title='Distance from source = {0:02d} [mm]'.format(c_dist))
        plot.baseName = 'dist_' + str(1000 + c_dist)
        plot.saveName = 'png/source/' + plot.baseName + '.png'
	# Also save pickle for lens' entrance position to calculate transmission
	if c_dist == step * (N_ - 1):
		plot.persistentName = 'pickle/source/' + plot.baseName + '.pickle'
        plots.append(plot)
    xrtr.run_ray_tracing(plots, repeats=repeats, beamLine=beamLine, processes=processes)

if __name__ == '__main__':
    main()
        
        
        

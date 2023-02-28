import time
import os
import subprocess
import argparse
import requests
import xmltodict

def str2time(str):
    if len(str) > 20:
        return time.mktime(time.strptime(str, '%Y-%m-%dT%H:%M:%S.%fZ'))
    elif len(str) > 14:
        return time.mktime(time.strptime(str, '%Y-%m-%dT%H:%M:%SZ'))
    elif len(str) == 14:
        return time.mktime(time.strptime(str, '%Y%m%d%H%M%S'))
    else:
        return 0

def getFPL(fufi):
    x = requests.get(urlFP + '/flightplan/' + fufi)  # get all flightplans
    if not x.ok:
        return 'no_fpl', None
    else:
        dict = xmltodict.parse(x.content.decode())
        if 'flightplans' in dict:  # multiple flightplans exist
            fpl = dict['flightplans']['flightplan']
        else:
            fpl = dict['flightplan']
        if isinstance(fpl, list):
            fpl = fpl[0]
    return 'ok', fpl

def writeflight(fpl):
    traj = fpl['trajectories']['trajectory']
    if isinstance(traj, list):
        traj = traj[0]
    flk = fpl['flightKey']['naturalKey']
    filename = '{}{}_{}-{}.txt'.format(flk['fPrefix']['@icao'],flk['fNumber'],flk['dep']['airportCode'][1]['#text'],flk['dst']['airportCode'][1]['#text'])
    out = open(filename, 'w')
    out.write('AIR NEW ZEALAND FLIGHT PLAN\n')
    actype = fpl['aircraft']['version'][:4]
    out.write('{}\n'.format(actype))
    out.write('DESP\n')
    out.write('ZKOKR\n')
    out.write('PDA\n')
    out.write('\n')
    blkfuel = float(fpl['masses']['fuelMass']['planned'])
    points = traj['trajectoryPoint']
    fuel = blkfuel
    for point in points:
        pointinfo = point['pointInfo']
        if not 'pointIdentifier' in pointinfo:
            continue
        if not '@type' in point:
            continue
        type = point['@type']
        if not type in ['PA','EA','D','DB','PC','PG']:
            continue
        ident = pointinfo['pointIdentifier']
        if 'altitude' in pointinfo:
            alt = float(pointinfo['altitude']['altitudeStd']['#text'])
        else:
            alt = 0
        if 'InbSegInfo' in point:
            seginfo = point['InbSegInfo']
            phase = seginfo['@segmentPhase']
            fuel -= float(seginfo['fuel'])
            tme = float(seginfo['time'])
            temp = int(float(seginfo['temp']['@SAT'])-273.5)
            mach = float(seginfo['speed']['mach']['#text'])
        else:
            phase = 'Ground'
            tme = 0
            temp = 15
            mach = 0
        # temp = -75
        if temp >= 0:
            sat = 'P{}'.format(temp)
        else:
            sat = 'M{}'.format(abs(temp))
        out.write('WP {}\n'.format(ident))
        if phase == 'Cruise' and alt >= 100:
            out.write('                       {} {:03d}  F{:03d}        {}\n'.format(sat, int(mach*1000), int(alt), int(tme/60)))
        else:
            out.write('                                            {}\n'.format(int(tme / 60)))
        out.write('                                               {:3.1f}\n'.format(fuel/1000))
        out.write('\n')
    out.write('\n')
    out.write('NET FUEL {}\n'.format(int(blkfuel)))
    out.close()
    return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='mode parameters')
    parser.add_argument('server')
    parser.add_argument('fufi')
    args = parser.parse_args()
    baseUrl = 'http://{}.flightkeys.com:8080'.format(args.server)
    endpointFP = '/service-flightplanapi/api/v1'
    urlFP = baseUrl + endpointFP
    status, fpl = getFPL(args.fufi)
    if status != 'ok':
        print('cannot retrieve flightplan')
        quit()
    filename = writeflight(fpl)
    cmdline = 'anzftpp.exe '+ filename
    result = subprocess.call(cmdline)
    print('all OK')



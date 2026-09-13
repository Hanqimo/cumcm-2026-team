"""Offline interface-shape check using only the supplied public Robot.

Run through the sole shared run_local.py factory option. No physics copy/HTTP.
"""
from strategy import Planner

class TupleRobot:
    def __init__(self,robot):self.__robot=robot
    @property
    def position(self):return tuple(float(x) for x in self.__robot.position)
    @property
    def channel(self):return self.__robot.channel
    @property
    def cleared(self):return self.__robot.cleared
    def record(self,value):self.__robot.record(value)
    def measure(self,point,channel):
        z=self.__robot.measure(point,channel)
        return dict(z,accepted=True,request_id='offline-public-interface-check')
    def clear(self,point,channel):return self.__robot.clear(point,channel)

def make(robot,policy='both'):
    return Planner(TupleRobot(robot),policy=policy)

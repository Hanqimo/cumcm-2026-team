"""Combine the independently developed localization and scan-cover candidates."""
from cost_aware import CostAwarePlanner
from merged_cover import MergedCoverPlanner


class CombinedCostCoverPlanner(CostAwarePlanner):
    candidates = MergedCoverPlanner.candidates

    def __init__(self, robot, *, merge_stations=True, merge_target_scans=True, **kwargs):
        super().__init__(robot, **kwargs)
        self.merge_stations = merge_stations
        self.merge_target_scans = merge_target_scans

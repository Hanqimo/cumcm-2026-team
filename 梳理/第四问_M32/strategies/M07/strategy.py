"""Frozen J500 planner with an official HTTP-compatible lifecycle wrapper."""
import json
from pathlib import Path
from research_strategy import Planner as Integrated

VERSION = 'p4-m07-portfolio-official-v1'
POLICIES = json.loads(Path(__file__).with_name('policies.json').read_text(encoding='utf-8'))


class Planner(Integrated):
    def __init__(self, robot, *, policy='baseline'):
        if policy != 'baseline':
            raise ValueError(policy)
        super().__init__(robot, 'baseline')
        self.stop_reason = None

    def run(self):
        try:
            self.stop_reason = super().run()
        finally:
            self.robot.scanned_sites = len(self.visited)
        return self.stop_reason

    def certificate(self):
        return dict(problem=4, reason=self.stop_reason, complete=bool(self.stop_reason),
            cleared_channels=sorted(self.robot.cleared),
            observed_but_uncleared=sorted(set(self.tracks) - set(self.robot.cleared)),
            mesh_points=self.sites.tolist(), visited_sites=sorted(self.visited),
            negative_counts={str(ch):len(points) for ch,points in self.negatives.items()},
            deferred=self.deferred, shared_measures=self.shared_measures,
            optical_fallbacks=self.fallbacks, known_channel_radio_losses=self.lost,
            assumptions='M16: fixed 22-site continuous coverage, posterior planning only, original MEC and finite optical clearance')

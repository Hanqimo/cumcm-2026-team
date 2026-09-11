"""Loopback mock HTTP only, random OS port, never the simulator's port."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from api_client import Robot


class ClientTests(unittest.TestCase):
    def run_server(self, replies, check):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                requests.append((self.path, body))
                reply = replies[min(len(requests) - 1, len(replies) - 1)]
                if reply is None:
                    self.close_connection = True
                    return
                raw = reply if isinstance(reply, bytes) else json.dumps(reply).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                robot = Robot('LOCAL-TEST', f'http://127.0.0.1:{server.server_port}', Path(directory) / 'run')
                robot.started = time.monotonic()
                try:
                    check(robot, requests)
                finally:
                    robot.log.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_lost_reply_same_bytes_rejection_keeps_clock_position(self):
        def check(robot, requests):
            robot.measure((300., 400.), 2)
            self.assertEqual(requests[0], requests[1])
            self.assertEqual(robot.position, (300., 400.))
            self.assertEqual(robot.distance_m, 500.)
            self.assertEqual(robot.channel, 2)
            with self.assertRaises(RuntimeError):
                robot.measure((500., 800.), 3)
            self.assertEqual(robot.virtual, 106.)
            self.assertEqual(robot.position, (300., 400.))
            self.assertEqual(robot.channel, 2)
            self.assertFalse(robot.transport_uncertain)
            self.assertNotEqual(json.loads(requests[1][1])['request_id'], json.loads(requests[2][1])['request_id'])
        self.run_server([None, dict(accepted=True, virtual_time_s=106, measure_result='no_signal'),
                         dict(accepted=False, virtual_time_s=0)], check)

    def test_malformed_reply_retry_then_clear_keeps_measurement_channel(self):
        def check(robot, requests):
            robot.measure((0., 0.), 7)
            self.assertEqual(requests[0], requests[1])
            robot.clear((0., 0.), 8)
            self.assertEqual(robot.channel, 7)
            self.assertEqual(robot.switches, 1)
            self.assertEqual(robot.cleared, {8})
        self.run_server([b'{bad json', dict(accepted=True, virtual_time_s=6, measure_result='no_signal'),
                         dict(accepted=True, virtual_time_s=11, clear_result='success')], check)

    def test_permanent_uncertainty_blocks_exit_and_new_actions(self):
        def check(robot, requests):
            with self.assertRaises(RuntimeError):
                robot.measure((1., 2.), 1)
            self.assertEqual(len(requests), 3)
            self.assertTrue(all(r == requests[0] for r in requests))
            self.assertTrue(robot.transport_uncertain)
            with self.assertRaises(RuntimeError):
                robot.call('/exit')
            self.assertEqual(len(requests), 3)
            self.assertEqual(robot.position, (0., 0.))
        self.run_server([None], check)

    def test_full_cli_against_independent_http_world(self):
        from verify import World, scene
        world = World(scene(31), 31)
        seen = {}
        errors = []
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                paths.append(self.path)
                expected = {'arena_id', 'robot_id', 'request_id'}
                if self.path in ('/measure', '/clear'):
                    expected |= {'position', 'channel'}
                if set(payload) != expected:
                    errors.append('unexpected fields')
                if payload['request_id'] in seen:
                    data = seen[payload['request_id']]
                else:
                    data = {'accepted': True, 'real_timestamp_ms': 0}
                    if self.path == '/enter':
                        data['remaining_real_duration_s'] = 1200
                    elif self.path == '/measure':
                        point = (payload['position']['x'], payload['position']['y'])
                        data.update(world.measure(point, payload['channel']))
                    elif self.path == '/clear':
                        point = (payload['position']['x'], payload['position']['y'])
                        data['clear_result'] = 'success' if world.clear(point, payload['channel']) else 'no_target_in_range'
                    elif self.path != '/exit':
                        errors.append('unexpected path')
                    data['virtual_time_s'] = world.virtual
                    seen[payload['request_id']] = data
                raw = json.dumps(data).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                package = Path(directory) / 'package'
                package.mkdir()
                for source in (Path(__file__).resolve().parents[1] / 'src').glob('*.py'):
                    shutil.copy2(source, package / source.name)
                result = subprocess.run([sys.executable, str(package / 'run_robot.py'),
                                         '--team', 'LOCAL-TEST', '--port', str(server.server_port)],
                                        input='\n', text=True, capture_output=True, timeout=30,
                                        encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                summary = json.loads(next((package / 'runs').glob('*/summary.json')).read_text(encoding='utf-8'))
                self.assertEqual(summary['outcome'], 'completed')
                self.assertTrue(summary['exit_confirmed'])
                self.assertEqual(world.cleared, set(world.targets))
                self.assertAlmostEqual(summary['distance_m'], world.distance_m, places=5)
                self.assertAlmostEqual(summary['virtual_time_s'], world.virtual, places=5)
                self.assertEqual(summary['switches'], world.switches)
                self.assertEqual(paths[0], '/enter')
                self.assertEqual(paths[-1], '/exit')
                self.assertEqual(errors, [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main(verbosity=2)

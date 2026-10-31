import json
import os
import tempfile
import unittest
import zipfile

from wtpoligon import logs


class TestLogs(unittest.TestCase):
    def test_collect_without_game_logs(self):
        with tempfile.TemporaryDirectory() as d:
            game, app, out = (os.path.join(d, x) for x in ('game', 'app', 'out'))
            os.makedirs(os.path.join(app, 'installs', 'x'))
            with open(os.path.join(app, 'installs', 'x', 'manifest.json'), 'w') as f:
                f.write('{}')
            os.makedirs(game)
            path = logs.collect(game, app, out)
            with zipfile.ZipFile(path) as z:
                self.assertIn('program/installs/x/manifest.json', z.namelist())
                info = json.loads(z.read('info.json'))
            self.assertEqual(info['game_logs'], [])


if __name__ == '__main__':
    unittest.main()

"""Recordes por fase e preferência de som; não grava nada dentro do código."""
import json
import math
import os
from pathlib import Path
import sys


def default_save_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local')))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    return root / 'MineirinhoPygame' / 'progresso.json'


class Progress:
    def __init__(self, path=None, enabled=True):
        self.path = Path(path) if path is not None else default_save_path()
        self.enabled = enabled
        self.best_times = {}
        self.completed = set()
        self.sound = True
        self.warning = ''
        if enabled:
            self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return
            self.sound = data.get('sound') is not False
            times = data.get('best_times', {})
            if isinstance(times, dict):
                self.best_times = {k:float(v) for k,v in times.items() if isinstance(k,str)
                                   and type(v) in (int,float) and math.isfinite(v) and 0 < v < 86400}
            completed = data.get('completed', [])
            if isinstance(completed, list):
                self.completed = {v for v in completed if isinstance(v,str)}
        except (OSError, ValueError, TypeError):
            pass

    def record(self, level_id, seconds):
        self.completed.add(level_id)
        best = self.best_times.get(level_id)
        if math.isfinite(seconds) and seconds > 0 and (best is None or seconds < best):
            self.best_times[level_id] = seconds
        self.save()

    def save(self):
        if not self.enabled:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(dict(version=1, sound=self.sound,
                           best_times=self.best_times, completed=sorted(self.completed)), ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(self.path)
            self.warning = ''
        except OSError:
            self.warning = 'Não foi possível salvar o progresso neste computador.'

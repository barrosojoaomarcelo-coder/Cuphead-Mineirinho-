"""CADASTRO DAS FASES: acrescente a importação e a classe na lista LEVELS."""
from .level_01 import Level01
from .level_02 import Level02
from .level_03 import Level03

LEVELS = [Level01, Level02, Level03]


def get_level(level_id):
    return next((level for level in LEVELS if level.id == level_id), None)


def next_available(level_id):
    index = next((i for i, level in enumerate(LEVELS) if level.id == level_id), -1)
    return next((level for level in LEVELS[index+1:] if level.available), None) if index >= 0 else None

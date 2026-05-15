from pathlib import Path

import yaml

from altamira.config.model import ProjectConfig

CONFIG_FILENAME = "altamira.yaml"


def load_config(root: Path = Path(".")) -> ProjectConfig:
    data = yaml.safe_load((root / CONFIG_FILENAME).read_text())
    return ProjectConfig.model_validate(data)


def write_config(config: ProjectConfig, root: Path = Path(".")) -> None:
    (root / CONFIG_FILENAME).write_text(
        yaml.dump(config.model_dump(), default_flow_style=False, sort_keys=False)
    )

from dataclasses import dataclass

from PPpackage_utils.utils import Installations, RunnerInfo


@dataclass
class Data:
    runner_info: RunnerInfo
    installations: Installations

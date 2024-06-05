REGISTRY = {}

from .basic_controller import BasicMAC
from .separate_controller import SeparateMAC
from .rode_controller import RODEMAC
from .noise_controller import NoiseMAC
from .macro_controller import MacroMAC
from .value_controller import ValueMAC

REGISTRY["basic_mac"] = BasicMAC
REGISTRY["separate_mac"] = SeparateMAC
REGISTRY["rode_mac"] = RODEMAC
REGISTRY["noise_mac"] = NoiseMAC
REGISTRY["macro_mac"] = MacroMAC
REGISTRY["value_mac"] = ValueMAC
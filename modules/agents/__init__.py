REGISTRY = {}

from .rnn_agent import RNNAgent
from .latent_ce_dis_rnn_agent import LatentCEDisRNNAgent
from .rode_agent import RODEAgent
from .G2ANet_agent import G2ANet
from .noise_rnn_agent import NoiseRNNAgent
from .macro_agent import MacroAgent
from .value_agent import VALUEAgent
REGISTRY["rnn"] = RNNAgent
REGISTRY["latent_ce_dis_rnn"] = LatentCEDisRNNAgent
REGISTRY["rode"] = RODEAgent
REGISTRY["G2ANet"] = G2ANet
REGISTRY["noise_rnn"] = NoiseRNNAgent
REGISTRY["macro"] = MacroAgent
REGISTRY["value"] = VALUEAgent
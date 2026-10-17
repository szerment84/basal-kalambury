"""basal-serve z jedną poprawką dla Apple Silicon: tabela per-layer embeddings zostaje w RAM-ie CPU.

basal-omni-1.0-mini (Gemma 4 E4B) ma 2,8 mld parametrów (5,6 GB w fp16) w embed_tokens_per_layer, a każde zapytanie
czyta z niej tylko wiersze swoich tokenów. Na MPS cały bufor jest przypinany do GPU przy każdym przebiegu, co przy
zajętej pamięci kosztuje sekundy. Na CPU odczyt daje identyczne liczby (to kopia wierszy; logity różnią się o 0,0),
a GPU trzyma ~10 GB zamiast ~16 GB. Na CUDA i CPU nic się nie zmienia. Argumenty idą bez zmian do basal-serve:

  python -m kalambury.serve --model Remek/basal-omni-1.0-mini --mode eager --device mps --dtype float16 --media on
"""
import torch
from basal import engine, server

_init = engine.EagerBackend.__init__


def _init_ple_on_cpu(self, *args, **kwargs):
    _init(self, *args, **kwargs)
    ple = getattr(getattr(getattr(self.model, "model", None), "language_model", None), "embed_tokens_per_layer", None)
    if ple is None or self.dev != "mps":
        return
    dev = self.dev
    ple.to("cpu")
    ple.register_forward_pre_hook(lambda mod, args: (args[0].cpu(),))
    ple.register_forward_hook(lambda mod, args, out: out.to(dev))
    torch.mps.empty_cache()
    print("kalambury: embed_tokens_per_layer na CPU", flush=True)


engine.EagerBackend.__init__ = _init_ple_on_cpu

if __name__ == "__main__":
    server.main()

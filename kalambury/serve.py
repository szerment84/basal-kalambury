"""basal-serve with one fix for Apple Silicon: the per-layer embedding table stays in CPU RAM.

basal-omni-1.0-mini (Gemma 4 E4B) has 2.8B parameters (5.6 GB in fp16) in embed_tokens_per_layer, and each request
reads only the rows of its own tokens. On MPS the whole buffer is pinned to the GPU on every forward pass, which costs
seconds when memory is tight. On the CPU the lookup gives identical numbers (it copies rows; the logits differ by 0.0)
and the GPU holds ~10 GB instead of ~16 GB. Nothing changes on CUDA or CPU. Arguments go to basal-serve unchanged:

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
    print("kalambury: embed_tokens_per_layer on the CPU", flush=True)


engine.EagerBackend.__init__ = _init_ple_on_cpu

if __name__ == "__main__":
    server.main()

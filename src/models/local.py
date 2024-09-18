import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict
from models.base import LocalModel

class MiniCPM3LocalModel(LocalModel):
  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False):
    super().__init__(model_name, model_path, defer_loading)
    self.tokenizer = None
    self.device = "cuda" if torch.cuda.is_available() else "cpu"

  def load(self) -> None:
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
    self.model = AutoModelForCausalLM.from_pretrained(
      self.model_path,
      torch_dtype=torch.bfloat16,
      device_map=self.device,
      trust_remote_code=True
    )

  def unload(self) -> None:
    self.model = None
    self.tokenizer = None
    torch.cuda.empty_cache()

  def tokenize(self, text: str) -> List[int]:
    return self.tokenizer.encode(text)

  def detokenize(self, tokens: List[int]) -> str:
    return self.tokenizer.decode(tokens)

  def generate(self, messages: list, **kwargs) -> str:
    model_inputs = self.tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(self.device)

    model_outputs = self.model.generate(
      model_inputs,
      max_new_tokens=kwargs.get('max_new_tokens', 1024),
      top_p=kwargs.get('top_p', 0.7),
      temperature=kwargs.get('temperature', 0.7)
    )

    output_token_ids = model_outputs[0][len(model_inputs[0]):]
    response = self.tokenizer.decode(output_token_ids, skip_special_tokens=True)
    return response

  def download(self, model_path: str) -> None:
    # Implement the download logic here
    # You might use Hugging Face's snapshot_download or a custom downloader
    pass

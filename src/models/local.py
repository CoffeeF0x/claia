import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict
from models.base import LocalModel

class MiniCPM3LocalModel(LocalModel):
  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device = "cpu"):
    model_path = os.path.join(model_path, "MiniCPM3-4B")
    super().__init__(model_name, model_path, defer_loading, device)

  def load(self) -> None:
    if not os.path.exists(self.model_path):
      self.download(self.model_path)

    self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
    self.model = AutoModelForCausalLM.from_pretrained(
      self.model_path,
      torch_dtype=torch.bfloat16,
      device_map=self.device,
      trust_remote_code=True
    )
    self.loaded = True

  def unload(self) -> None:
    self.model = None
    self.tokenizer = None
    torch.cuda.empty_cache()
    self.loaded = False

  def tokenize(self, text: str) -> List[int]:
    return self.tokenizer.encode(text)

  def detokenize(self, tokens: List[int]) -> str:
    return self.tokenizer.decode(tokens, skip_special_tokens=True)

  def generate(self, messages: list, **kwargs) -> str:
    if not self.is_loaded():
      self.load()

    model_inputs = self.tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(self.device)

    model_outputs = self.model.generate(
      model_inputs,
      max_new_tokens=kwargs.get('max_new_tokens', 1024),
      top_p=kwargs.get('top_p', 0.7),
      temperature=kwargs.get('temperature', 0.7)
    )

    output_token_ids = model_outputs[0][len(model_inputs[0]):]
    response = self.detokenize(output_token_ids)
    return response

  def download(self, model_path: str) -> None:
    print(f"Downloading MiniCPM3-4B model to {model_path}")
    os.makedirs(model_path, exist_ok=True)

    AutoModelForCausalLM.from_pretrained(
      "openbmb/MiniCPM3-4B",
      torch_dtype=torch.bfloat16,
      trust_remote_code=True
    ).save_pretrained(model_path)

    AutoTokenizer.from_pretrained(
      "openbmb/MiniCPM3-4B",
      trust_remote_code=True
    ).save_pretrained(model_path)

    print("Model downloaded successfully")

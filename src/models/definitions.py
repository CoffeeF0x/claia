# NOTE: All key names MUST be lowercase

definitions = {
  "gpt-3.5-turbo": {
    "title": "GPT 3.5 Turbo",
    "description": "The latest GPT-3.5 Turbo model with higher accuracy at responding in requested formats and a fix for a bug which caused a text encoding issue for non-English language function calls.",
    "variants": ["gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106", "gpt-3.5-turbo-instruct"],
    "sources": ["openai", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 4096,
      "context": 16385,
      "training_data": "Up to September 2021",
    },
  },
  "gpt-4": {
    "title": "GPT 4",
    "description": "Snapshot of gpt-4 from June 13th 2023 with improved function calling support.",
    "variants": ["gpt-4-0613", "gpt-4-0314"],
    "sources": ["openai", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 8192,
      "context": 8192,
      "training_data": "Up to September 2021",
    },
  },
  "gpt-4-turbo": {
    "title": "GPT 4 Turbo",
    "description": "The latest GPT-4 Turbo model with vision capabilities. Vision requests can now use JSON mode and function calling.",
    "variants": ["gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview", "gpt-4-0125-preview", "gpt-4-1106-preview"],
    "sources": ["openai", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 4096,
      "context": 128000,
      "training_data": "Up to December 2023",
    },
  },
  "claude-3-5-sonnet-20240620": {
    "title": "Claude 3.5 Sonnet",
    "description": "Claude 3.5 Sonnet sets new industry benchmarks for graduate-level reasoning (GPQA), undergraduate-level knowledge (MMLU), and coding proficiency (HumanEval). It shows marked improvement in grasping nuance, humor, and complex instructions, and is exceptional at writing high-quality content with a natural, relatable tone.",
    "variants": [],
    "sources": ["anthropic", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 8192,
      "context": 200000,
      "training_data": "Up to April 2024",
    },
  },
  "minicpm3-4b": {
    "title": "MiniCPM3-4B",
    "description": "MiniCPM3-4B is the 3rd generation of MiniCPM series with a 32k context window.",
    "variants": [],
    "sources": ["local-minicpm3-4b", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 1024,
      "context": 32000,
      "training_data": "Not specified",
    },
  },
  "qwen2.5-32b-instruct": {
    "title": "Qwen2.5-32B-Instruct",
    "description": "Qwen2.5 is the latest series of Qwen large language models. For Qwen2.5, we release a number of base language models and instruction-tuned language models ranging from 0.5 to 72 billion parameters.",
    "variants": [],
    "sources": ["local-qwen2.5-32b-instruct", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 8192,
      "context": 131072,
      "training_data": "Not specified",
    },
  },
  "qwen2.5-72b-instruct": {
    "title": "Qwen2.5-72B-Instruct",
    "description": "Qwen2.5's largest model with 72B parameters. Features improved capabilities in coding, mathematics, instruction following, and multilingual support for over 29 languages. Specialized in generating structured outputs and long-form content.",
    "variants": [],
    "sources": ["runpod", "openrouter"],
    "capabilities": ["ttt"],
    "inputs": ["text"],
    "outputs": ["text"],
    "attributes": {
      "max_output": 8192,
      "context": 131072,
      "training_data": "Not specified",
    },
  },
  # {
  #   "name": "whisper-v3-large",
  #   "variants": [],
  #   "description": "The third release of Whisper, a speech to text transcription model by OpenAI",
  #   "title": "Whisper v3",
  # }
}

abbreviations = {
  "ttt": "text-to-text",
  "tti": "text-to-image",
  "itt": "image-to-text",
  "tts": "text-to-speech",
  "stt": "speech-to-text",
  "tta": "text-to-audio",
  "llm": "large-language-model",
  "slm": "small-language-model"
}

types = {
  "text": ["txt"],
  "text-vision": ["txt", "png", "jpg"],
  "image": ["png", "jpg"],
}

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
import logging

# Internal dependencies
from results import Result
from files import Conversation


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class BaseModel(ABC):
  def __init__(self, model_name: str):
    self.model_name = model_name

  @abstractmethod
  def generate(self, conversation: Conversation, **kwargs) -> Conversation:
    """Generate a response based on the given prompt."""
    pass

  # @property
  # @abstractmethod
  # def max_tokens(self) -> int:
  #   """Return the maximum number of tokens the model can handle."""
  #   pass

  # @abstractmethod
  # def get_model_info(self) -> Dict[str, Any]:
  #   """Return information about the model."""
  #   pass


class APIModel(BaseModel):
  def __init__(self, model_name: str, base_url: str):
    super().__init__(model_name)
    self.base_url = base_url
    self.session = requests.Session()

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for authentication."""
    self.set_custom_header("Authorization", f"Bearer {api_key}")

  def set_custom_header(self, header_name: str, header_value: str) -> None:
    """Set a custom header for authentication or other purposes."""
    self.session.headers.update({header_name: header_value})

  def request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, *args, **kwargs) -> requests.Response:
    """Make an API request with the configured session."""
    url = f"{self.base_url}/{endpoint}"
    response = self.session.request(method, url, json=data, params=params, *args, **kwargs)
    response.raise_for_status()
    return response

  def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
    """Make a GET request to the API."""
    return self.request("GET", endpoint, params=params)

  def post(self, endpoint: str, data: Dict, *args, **kwargs) -> requests.Response:
    """Make a POST request to the API."""
    return self.request("POST", endpoint, data=data, *args, **kwargs)

  def put(self, endpoint: str, data: Dict) -> requests.Response:
    """Make a PUT request to the API."""
    return self.request("PUT", endpoint, data=data)

  def delete(self, endpoint: str) -> requests.Response:
    """Make a DELETE request to the API."""
    return self.request("DELETE", endpoint)


class LocalModel(BaseModel):
  model = None

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu"):
    super().__init__(model_name)
    self.model_path = model_path
    self.loaded = not defer_loading
    self.device = device

    if not defer_loading:
      self.load()

  def is_loaded(self) -> bool:
    return self.loaded

  @abstractmethod
  def load(self) -> None:
    """Load the model."""
    pass

  @abstractmethod
  def unload(self) -> None:
    """Unload the model."""
    self.model = None

  @abstractmethod
  def tokenize(self, text: str) -> List[int]:
    """Tokenize the input text."""
    pass

  @abstractmethod
  def detokenize(self, tokens: List[int]) -> str:
    """Convert tokens back to text."""
    pass

  @abstractmethod
  def download(self, model_path: str) -> None:
    """Download the model to the specified path."""
    pass

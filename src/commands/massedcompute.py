from commands.base import Command
from errors import Result
from settings import Settings
import help
import requests
from typing import Optional, Dict, Any, List
import logging

##################################################
#                  CONSTANTS                     #
##################################################
STARTUP_SCRIPTS = {
  "jupyter": [
    "#!/bin/bash",
    "pip3 install jupyterlab",
    "jupyter lab --ip=0.0.0.0 --port=8888 --allow-root --no-browser",
    "--NotebookApp.token='' --NotebookApp.password=''"
  ],
  "ssh": [
    "#!/bin/bash",
    "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config",
    "systemctl restart sshd"
  ],
  "pytorch": [
    "#!/bin/bash",
    "pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
  ],
  "tensorflow": [
    "#!/bin/bash",
    "pip3 install tensorflow tensorflow-gpu",
    "python3 -c \"import tensorflow as tf; print('TensorFlow version:', tf.__version__);",
    "print('GPU Available:', tf.config.list_physical_devices('GPU'))\""
  ]
}

##################################################
#                 COMMAND CLASS                  #
##################################################
class MassedComputeCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if not settings.has_massed_compute_api_token:
      print("MassedCompute API token not found. Please set TOKEN_MASSEDCOMPUTE in your environment.")
      return result

    if len(commands) > 1:
      if commands[1] == "deploy":
        deployInstance(settings, commands[2:])
      elif commands[1] == "terminate":
        terminateInstances(settings, commands[2:])
      elif commands[1] == "details":
        if len(commands) > 2:
          getInstanceDetails(settings, commands[2])
        else:
          print("Error: Must specify instance UUID")
      elif commands[1] == "list":
        if len(commands) <= 2 or commands[2] in ["instance", "instances"]:
          listInstances(settings)
        elif commands[2] in ["gpu", "gpus"]:
          listGPUs(settings)
        elif commands[2] in ["image", "images"]:
          listImages(settings)
        else:
          help.unrecognizedCommand()
      else:
        help.unrecognizedCommand()
    else:
      help.massedcomputeCommands()

    return result

##################################################
#                HELPER FUNCTIONS                #
##################################################
def format_images_table(images: List[Dict[str, Any]]) -> List[str]:
  """Formats image data into printable table rows."""
  if not images:
    return ["No images available"]
    
  output = []
  
  for image in images:
    # Add ID and name on first line
    output.append(f"{image['vm_image_id']} {image['vm_image_name']}")
    
    # Split description by newlines first
    desc_parts = image['vm_image_description'].split('\n')
    
    for desc in desc_parts:
      desc = desc.strip()
      if not desc:  # Skip empty lines
        continue
        
      first_line = True
      # Wrap at 68 chars to account for 4 space indent (72 char limit)
      while desc:
        max_length = 68 if first_line else 66  # Account for "  " prefix on continuation
        if len(desc) <= max_length:
          prefix = "    - " if first_line else "      "
          output.append(f"{prefix}{desc}")
          break
        
        # Find last space before max_length
        split_idx = desc[:max_length].rstrip().rfind(' ')
        if split_idx == -1:
          split_idx = max_length
        
        prefix = "    - " if first_line else "      "
        output.append(f"{prefix}{desc[:split_idx]}")
        desc = desc[split_idx:].lstrip()
        first_line = False
    
    output.append("")  # Add blank line between images
    
  return output[:-1]  # Remove last blank line

def format_instances_table(instances: List[Dict[str, Any]]) -> List[str]:
  """Formats instance data into printable table rows."""
  if not instances:
    return ["No running instances"]
    
  output = [
    "\nRunning Instances:",
    "-" * 100,
    f"{'Name':<20} {'UUID':<40} {'Status':<10} {'IP':<15} Product",
    "-" * 100,
  ]
  
  for instance in instances:
    name = instance.get('name', 'N/A')[:19]
    uuid = instance.get('uuid', 'N/A')
    status = instance.get('status', 'N/A')
    ip = instance.get('ip', 'N/A')
    product = instance.get('product', {}).get('name', 'N/A')
    
    output.append(f"{name:<20} {uuid:<40} {status:<10} {ip:<15} {product}")
    
  return output

def get_startup_script(script_name: str) -> Optional[str]:
  """
  Get a startup script by name, joining the commands with && if found.
  
  Args:
      script_name: Name of the script to retrieve
      
  Returns:
      Joined script commands if found, None otherwise
  """
  if script_name not in STARTUP_SCRIPTS:
    return None
  return " && ".join(STARTUP_SCRIPTS[script_name])

##################################################
#                   FUNCTIONS                    #
##################################################
def deployInstance(settings: Settings, args: list[str]) -> None:
  try:
    api = MassedComputeAPI(settings)
    
    # Default image ID and optional name handling
    image_id = 18  # Default image ID
    instance_name = None
    startup_script = None
    
    # Parse arguments
    if len(args) > 0:
      try:
        image_id = int(args[0])
      except ValueError:
        print(f"Invalid image ID: {args[0]}")
        return
        
    if len(args) > 1:
      instance_name = args[1]
      
    if len(args) > 2:
      script_name = args[2].lower()
      startup_script = get_startup_script(script_name)
      if startup_script is None:
        print(f"Unknown startup script: {script_name}")
        print("Available scripts:", ", ".join(STARTUP_SCRIPTS.keys()))
        return
      
    response = api.deploy_cheapest_instance(image_id, instance_name, startup_script)
    instance_uuid = response.get('response')
    print(f"Deployed instance with UUID: {instance_uuid}")
    
  except Exception as e:
    print(f"Error: {str(e)}")

def listImages(settings: Settings) -> None:
  """Lists all available images that can be deployed."""
  try:
    api = MassedComputeAPI(settings)
    images = api.get_images()
    
    # Print formatted table
    for line in format_images_table(images):
      print(line)
      
  except Exception as e:
    print(f"Error listing images: {str(e)}")

def listInstances(settings: Settings) -> None:
  """Lists all running instances."""
  try:
    api = MassedComputeAPI(settings)
    instances = api.get_instances()
    
    # Print formatted table
    for line in format_instances_table(instances):
      print(line)
      
  except Exception as e:
    print(f"Error listing instances: {str(e)}")

def listGPUs(settings: Settings) -> None:
  """Lists all available GPU configurations."""
  try:
    api = MassedComputeAPI(settings)
    inventory = api.get_gpu_inventory()

    # Format and print GPU inventory
    print("\nAvailable GPU Configurations:")
    print("-" * 72)
    print(f"{'Product':<15} {'Description':<25} {'Price/Hr':<10} {'Available':<10}")
    print("-" * 72)

    for product_info in inventory.values():
      instance_type = product_info.get('instance_type', {})
      name = instance_type.get('name', 'N/A')
      desc = instance_type.get('description', 'N/A')
      price = instance_type.get('price_cents_per_hour', 0) / 100
      capacity = product_info.get('capacity_available', 0)

      print(f"{name[:15]:<15} {desc[:25]:<25} ${price:<9.2f} {capacity:<10}")

  except Exception as e:
    print(f"Error listing GPU inventory: {str(e)}")

def terminateInstances(settings: Settings, args: list[str]) -> None:
  """Terminates one or more instances by UUID."""
  if not args:
    print("Error: Must specify at least one instance UUID to terminate")
    return

  try:
    api = MassedComputeAPI(settings)
    response = api.terminate_instances(args)
    
    # Print results
    terminated = response.get('response', {}).get('data', {}).get('terminated_instances', [])
    if terminated:
      print("\nSuccessfully terminated instances:")
      for instance in terminated:
        name = instance.get('name', 'N/A')
        uuid = instance.get('id', 'N/A')
        print(f"  {name} ({uuid})")
    else:
      print("No instances were terminated")
      
  except Exception as e:
    print(f"Error terminating instances: {str(e)}")

def getInstanceDetails(settings: Settings, instance_uuid: str) -> None:
  """Gets detailed information about a specific instance."""
  try:
    api = MassedComputeAPI(settings)
    instance = api.get_instance_details(instance_uuid)
    
    if not instance:
      print(f"No instance found with UUID: {instance_uuid}")
      return
      
    # Print basic info
    print("\nInstance Details:")
    print("-" * 72)
    print(f"Name: {instance.get('name', 'N/A')}")
    print(f"UUID: {instance.get('uuid', 'N/A')}")
    print(f"Status: {instance.get('status', 'N/A')}")
    print(f"IP Address: {instance.get('ip', 'N/A')}")
    print(f"Username: {instance.get('username', 'N/A')}")
    print(f"Created: {instance.get('created', 'N/A')}")
    
    # Print image info
    image = instance.get('image', {})
    print("\nImage:")
    print(f"  ID: {image.get('id', 'N/A')}")
    print(f"  Name: {image.get('name', 'N/A')}")
    print(f"  Description: {image.get('description', 'N/A')}")
    
    # Print product info
    product = instance.get('product', {})
    print("\nProduct:")
    print(f"  Name: {product.get('name', 'N/A')}")
    print(f"  Description: {product.get('description', 'N/A')}")
    print(f"  GPU Count: {product.get('gpu_count', 'N/A')}")
    print(f"  vCPUs: {product.get('vcpu', 'N/A')}")
    print(f"  RAM: {product.get('ram', 'N/A')} GB")
    print(f"  Storage: {product.get('storage', 'N/A')} GB")
    print(f"  Price/Hour: ${float(product.get('price_hr', 0)):.2f}")
    
  except Exception as e:
    print(f"Error getting instance details: {str(e)}")

##################################################
#                     API                        #
##################################################
class MassedComputeAPI:
  def __init__(self, settings: Settings):
    """Initialize MassedCompute API client."""
    if not settings.has_massed_compute_api_token:
      raise ValueError("MassedCompute API token not found in settings")
      
    self.api_token = settings.massed_compute_api_token
    self.base_url = "https://vm.massedcompute.com/api/v1"
    self.headers = {
      "Authorization": f"Bearer {self.api_token}",
      "Content-Type": "application/json"
    }

  def get_images(self) -> List[Dict[str, Any]]:
    """Get list of available images from API."""
    response = requests.get(
      f"{self.base_url}/images",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('images', [])

  def get_instances(self) -> List[Dict[str, Any]]:
    """Get list of running instances from API."""
    response = requests.get(
      f"{self.base_url}/instance",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('runningInstances', [])

  def deploy_cheapest_instance(
    self, 
    image_id: int, 
    instance_name: Optional[str] = None,
    startup_script: Optional[str] = None
  ) -> Dict[str, Any]:
    """
    Deploy the cheapest available GPU instance.
    
    Args:
        image_id: The ID of the image to deploy
        instance_name: Optional name for the instance
        startup_script: Optional startup script to run on instance launch
        
    Returns:
        Dict containing the deployment response with instance UUID
    """
    # Get GPU inventory to find cheapest option
    inventory = self.get_gpu_inventory()

    # Find cheapest GPU with available capacity
    cheapest_price = float('inf')
    cheapest_product = None
    
    for product_info in inventory.values():
      price = product_info.get('instance_type', {}).get('price_cents_per_hour', float('inf'))
      capacity = product_info.get('capacity_available', 0)
      
      if capacity > 0 and price < cheapest_price:
        cheapest_price = price
        cheapest_product = product_info['instance_type']['name']

    if not cheapest_product:
      raise ValueError("No GPU instances currently available")

    # Deploy the instance
    deploy_data = {
      "imageId": image_id,
      "productName": cheapest_product,
      "regionName": "any"
    }
    
    if instance_name:
      deploy_data["instanceName"] = instance_name
      
    if startup_script:
      deploy_data["command"] = startup_script

    deploy_response = requests.post(
      f"{self.base_url}/instance/launch",
      headers=self.headers,
      json=deploy_data
    )
    deploy_response.raise_for_status()
    
    return deploy_response.json()

  def get_gpu_inventory(self) -> Dict[str, Any]:
    """Get GPU inventory information from API."""
    response = requests.get(
      f"{self.base_url}/gpu-inventory",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('gpu_inventory', {})

  def terminate_instances(self, instance_uuids: List[str]) -> Dict[str, Any]:
    """
    Terminate one or more instances.
    
    Args:
        instance_uuids: List of instance UUIDs to terminate
        
    Returns:
        API response containing termination results
    """
    response = requests.post(
      f"{self.base_url}/instance/terminate",
      headers=self.headers,
      json={"instanceUuids": instance_uuids}
    )
    response.raise_for_status()
    return response.json()

  def get_instance_details(self, instance_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific instance.
    
    Args:
        instance_uuid: UUID of the instance to query
        
    Returns:
        Dict containing instance details if found, None otherwise
    """
    response = requests.get(
      f"{self.base_url}/instance/{instance_uuid}",
      headers=self.headers
    )
    response.raise_for_status()
    return response.json().get('runningInstances')[0]

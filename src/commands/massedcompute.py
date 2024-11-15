from commands.base import Command
from errors import Result
from settings import Settings
import help
import requests
from typing import Optional, Dict, Any, List
import logging
import subprocess
import platform
import os

##################################################
#                  CONSTANTS                     #
##################################################
STARTUP_SCRIPTS = {
  "vllm": [
    # Create network for containers
    "docker network create vllm-network || true",
    
    # Create Traefik config directories
    "mkdir -p ~/traefik/config ~/traefik/acme ~/traefik/logs",
    
    # Create Traefik static config
    'echo "api:"                                                                          > ~/traefik/config/traefik.yml',
    'echo "  dashboard: true"                                                            >> ~/traefik/config/traefik.yml',
    'echo "  debug: false"                                                               >> ~/traefik/config/traefik.yml',
    'echo "  insecure: true"                                                             >> ~/traefik/config/traefik.yml',
    'echo "  disabledashboardad: true"                                                   >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "log:"                                                                         >> ~/traefik/config/traefik.yml',
    'echo "  level: \\"INFO\\""                                                          >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "ping: {{}}"                                                                   >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "providers:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "  docker:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "    endpoint: \\"unix:///var/run/docker.sock\\""                              >> ~/traefik/config/traefik.yml',
    'echo "    exposedByDefault: false"                                                  >> ~/traefik/config/traefik.yml',
    # 'echo "  file:"                                                                    >> ~/traefik/config/traefik.yml',
    # 'echo "    filename: \\"/etc/traefik/services.yaml\\""                             >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "accessLog:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "  filePath: \\"/logs/access.log\\""                                           >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "entryPoints:"                                                                 >> ~/traefik/config/traefik.yml',
    'echo "  web:"                                                                       >> ~/traefik/config/traefik.yml',
    'echo "    address: \\":80\\""                                                       >> ~/traefik/config/traefik.yml',
    'echo "    http:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      redirections:"                                                          >> ~/traefik/config/traefik.yml',
    'echo "        entryPoint:"                                                          >> ~/traefik/config/traefik.yml',
    'echo "          to: websecure"                                                      >> ~/traefik/config/traefik.yml',
    'echo "          scheme: https"                                                      >> ~/traefik/config/traefik.yml',
    'echo "  websecure:"                                                                 >> ~/traefik/config/traefik.yml',
    'echo "    address: \\":443\\""                                                      >> ~/traefik/config/traefik.yml',
    'echo ""                                                                             >> ~/traefik/config/traefik.yml',
    'echo "certificatesResolvers:"                                                       >> ~/traefik/config/traefik.yml',
    'echo "  letsencrypt:"                                                               >> ~/traefik/config/traefik.yml',
    'echo "    acme:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      email: \\"{email}\\""                                                   >> ~/traefik/config/traefik.yml',
    'echo "      caServer: \\"https://acme-v02.api.letsencrypt.org/directory\\""         >> ~/traefik/config/traefik.yml',
    'echo "      storage: \\"/acme/letsencrypt.json\\""                                  >> ~/traefik/config/traefik.yml',
    'echo "      tlsChallenge: {{}}"                                                     >> ~/traefik/config/traefik.yml',
    'echo "  staging:"                                                                   >> ~/traefik/config/traefik.yml',
    'echo "    acme:"                                                                    >> ~/traefik/config/traefik.yml',
    'echo "      email: \\"{email}\\""                                                   >> ~/traefik/config/traefik.yml',
    'echo "      caServer: \\"https://acme-staging-v02.api.letsencrypt.org/directory\\"" >> ~/traefik/config/traefik.yml',
    'echo "      storage: \\"/acme/staging.json\\""                                      >> ~/traefik/config/traefik.yml',
    'echo "      tlsChallenge: {{}}"                                                     >> ~/traefik/config/traefik.yml',
    
    # Start VLLM container
    "sudo docker run -d --name vllm --network vllm-network --runtime nvidia --ipc=host --gpus all " +
    "-v ~/.cache/huggingface:/root/.cache/huggingface " +
    "-e HUGGING_FACE_HUB_TOKEN={hf_token} " +
    "-l 'traefik.enable=true' " +
    "-l 'traefik.http.routers.vllm.rule=Host(`{subdomain}.{zone}`)' " +
    "-l 'traefik.http.routers.vllm.entrypoints=websecure' " +
    "-l 'traefik.http.routers.vllm.tls.certresolver=letsencrypt' " +
    "-l 'traefik.http.services.vllm.loadbalancer.server.port=8000' " +
    "vllm/vllm-openai:latest --model Qwen/Qwen2.5-72B-Instruct --max-model-len 26000 --tensor-parallel-size 4",
    
    # Start Traefik container
    "sudo docker run -d --name traefik --network vllm-network " +
    "-v /var/run/docker.sock:/var/run/docker.sock:ro " +
    "-v ~/traefik/config:/etc/traefik " +
    "-v ~/traefik/acme:/acme " +
    "-v ~/traefik/logs:/logs " +
    "-p 80:80 -p 443:443 " +
    # "-p 8080:8080 " +  # Added port for Traefik dashboard
    "traefik:latest",
    
    # Start DDNS updater container
    "sudo docker run -d --name ddns-updater " +
    "-e ZONE={zone} " +
    "-e SUBDOMAIN={subdomain} " +
    "-e API_KEY={cloudflare_token} " +
    "oznu/cloudflare-ddns:latest",
    
    # Print success message
    "echo 'Containers deployed successfully. VLLM will be available at https://{subdomain}.{zone} once DNS propagates'"
  ],
  "test": [
    "echo 'foxes will rule the world!' > /home/Ubuntu/test.txt"
  ]
}

SSH_CONNECT_TIMEOUT = "30"  # Timeout in seconds for SSH connection attempts

# GPU VRAM in GB for each GPU type
GPU_VRAM = {
  "a6000": 48,    # RTX A6000
  "h100": 80,     # H100
  "l40": 48,      # NVIDIA L40
  "a5000": 24,    # RTX A5000
  "l40s": 48,     # L40S
  "a100": 80,     # A100
  "a30": 24,      # NVIDIA A30
  "h100_nvl": 94  # H100 NVL
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
        if len(commands) > 2:
          if commands[2] == "cheapest":
            deployCheapestInstance(settings, commands[3:])
          elif commands[2] == "specific":
            deploySpecificInstance(settings, commands[3:])
          else:
            help.massedcomputeCommands()
        else:
          help.massedcomputeCommands()
      elif commands[1] == "terminate":
        terminateInstances(settings, commands[2:])
      elif commands[1] == "details":
        if len(commands) > 2:
          getInstanceDetails(settings, commands[2])
        else:
          print("Error: Must specify instance UUID")
      elif commands[1] == "ssh":
        if len(commands) > 2:
          sshToInstance(settings, commands[2])
        else:
          print("Error: Must specify instance UUID")
      elif commands[1] == "run":
        if len(commands) > 3:
          runScript(settings, commands[2], commands[3])
        else:
          print("Error: Must specify instance identifier and script name")
      elif commands[1] == "list":
        if len(commands) <= 2 or commands[2] in ["instance", "instances"]:
          listInstances(settings)
        elif commands[2] in ["gpu", "gpus"]:
          listGPUs(settings, commands)
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

def get_startup_script(script_name: str, settings: Optional[Settings] = None, extra_params: Optional[Dict[str, str]] = None) -> Optional[str]:
  """
  Get a startup script by name, joining the commands with && if found.
  
  Args:
      script_name: Name of the script to retrieve
      settings: Optional Settings object for token replacement
      extra_params: Optional dictionary of additional parameters to replace
      
  Returns:
      Joined script commands if found, None otherwise
  """
  if script_name not in STARTUP_SCRIPTS:
    return None
    
  script = " && ".join(STARTUP_SCRIPTS[script_name])
  
  # Create parameters dictionary
  params = {}
  
  # Add HuggingFace token if available
  if settings and settings.has_huggingface_api_token:
    params['hf_token'] = settings.huggingface_api_token
  
  # Add VLLM-specific parameters if available
  if settings:
    if settings.vllm_zone and settings.vllm_subdomain:
      params['subdomain'] = settings.vllm_subdomain
    if settings.vllm_email:
      params['email'] = settings.vllm_email
    if settings.vllm_zone:
      params['zone'] = settings.vllm_zone
    if settings.has_cloudflare_api_token:
      params['cloudflare_token'] = settings.cloudflare_api_token
  
  # Add any additional parameters
  if extra_params:
    params.update(extra_params)
  
  # Replace all parameters in the script
  try:
    script = script.format(**params)
  except KeyError as e:
    missing_param = str(e).strip("'")
    raise ValueError(f"Missing required parameter: {missing_param}")
    
  return script

def parse_extra_params(args: List[str]) -> Dict[str, str]:
  """Parse key=value parameters from argument list."""
  params = {}
  for arg in args:
    if '=' in arg:
      key, value = arg.split('=', 1)
      params[key] = value
  return params

##################################################
#                   FUNCTIONS                    #
##################################################
def deployCheapestInstance(settings: Settings, args: list[str]) -> None:
  """Deploy the cheapest available GPU instance."""
  try:
    api = MassedComputeAPI(settings)
    
    # Parse arguments
    if len(args) < 2:
      print("Error: Required arguments: <image_id> <instance_name>")
      return
      
    try:
      image_id = int(args[0])
    except ValueError:
      print(f"Invalid image ID: {args[0]}")
      return
      
    instance_name = args[1]
    startup_script = None
    ssh_keys = []
    
    # Handle optional startup script and parameters
    if len(args) > 2:
      script_name = args[2].lower()
      # Parse any extra parameters (format: key=value)
      extra_params = parse_extra_params(args[3:])
      
      startup_script = get_startup_script(script_name, settings, extra_params)
      if startup_script is None:
        print(f"Unknown startup script: {script_name}")
        print("Available scripts:", ", ".join(STARTUP_SCRIPTS.keys()))
        return
        
    # Handle optional SSH keys (any remaining args that aren't key=value)
    remaining_args = [arg for arg in args[3:] if '=' not in arg]
    if remaining_args:
      ssh_keys = handle_ssh_keys(remaining_args)
    
    response = api.deploy_cheapest_instance(
      image_id,
      instance_name,
      startup_script,
      ssh_keys
    )
    
    instance_uuid = response.get('response')
    print(f"Deployed instance with UUID: {instance_uuid}")
    if ssh_keys:
      print("Added SSH keys:")
      for key in ssh_keys:
        print(f"  - {key}")
        
  except Exception as e:
    print(f"Error: {str(e)}")

def deploySpecificInstance(settings: Settings, args: list[str]) -> None:
  """Deploy a specific GPU instance type."""
  try:
    api = MassedComputeAPI(settings)
    
    # Parse arguments
    if len(args) < 3:
      print("Error: Required arguments: <image_id> <instance_name> <product_name>")
      return

    try:
      image_id = int(args[0])
    except ValueError:
      print(f"Invalid image ID: {args[0]}")
      return
      
    instance_name = args[1]
    product_name = args[2].lower()  # Convert input to lowercase
    startup_script = None
    ssh_keys = []
    
    # Verify the product exists (case-insensitive)
    inventory = api.get_gpu_inventory()
    matching_products = [
      info['instance_type']['name'] 
      for info in inventory.values() 
      if info['instance_type']['name'].lower() == product_name
    ]
    
    if not matching_products:
      print(f"Error: Invalid product name '{args[2]}'")
      print("\nAvailable products:")
      for info in inventory.values():
        name = info['instance_type']['name']
        desc = info['instance_type']['description']
        print(f"  {name}: {desc}")
      return
    
    # Use the correct casing from the inventory
    product_name = matching_products[0]
    
    # Handle optional startup script
    if len(args) > 3:
      script_name = args[3].lower()
      startup_script = get_startup_script(script_name, settings)
      if startup_script is None:
        print(f"Unknown startup script: {script_name}")
        print("Available scripts:", ", ".join(STARTUP_SCRIPTS.keys()))
        return
        
    # Handle optional SSH keys
    if len(args) > 4:
      ssh_keys = handle_ssh_keys(args[4:])
    
    try:
      response = api.deploy_specific_instance(
        image_id,
        product_name,
        instance_name,
        startup_script,
        ssh_keys
      )
      
      instance_uuid = response.get('response')
      print(f"Deployed instance with UUID: {instance_uuid}")
      if ssh_keys:
        print("Added SSH keys:")
        for key in ssh_keys:
          print(f"  - {key}")
          
    except requests.exceptions.HTTPError as e:
      if e.response is not None:
        error_data = e.response.json()
        if 'response' in error_data:
          error_resp = error_data['response']
          if error_resp.get('code') == 'global/invalid_parameter' and 'capacity' in error_resp.get('message', '').lower():
            print(f"\nError: Not enough capacity for {product_name}")
            print("\nAvailable alternatives:")
            print("-" * 102)
            print(f"{'Product':<15} {'Description':<25} {'VRAM':<10} {'Price/Hr':<10} {'GB/$Hr':<10} {'Available':<10}")
            print("-" * 102)
            
            # Show available alternatives
            for info in inventory.values():
              instance_type = info.get('instance_type', {})
              capacity = info.get('capacity_available', 0)
              if capacity > 0:  # Only show products with capacity
                name = instance_type.get('name', 'N/A')
                desc = instance_type.get('description', 'N/A')
                price = instance_type.get('price_cents_per_hour', 0) / 100
                
                # Calculate VRAM and GB/$ per hour if possible
                vram = "N/A"
                gb_per_dollar = "N/A"
                for gpu_type, vram_amount in GPU_VRAM.items():
                  if gpu_type.lower() in name.lower():
                    multiplier = 1
                    if "gpu_" in name.lower() and "x_" in name.lower():
                      try:
                        multiplier = int(name.split("x_")[0].split("gpu_")[1])
                      except ValueError:
                        pass
                    total_vram = vram_amount * multiplier
                    vram = f"{total_vram}GB"
                    if price > 0:
                      gb_per_dollar = f"{total_vram/price:.1f}"
                    break
                
                print(f"{name[:15]:<15} {desc[:25]:<25} {vram:<10} ${price:<9.2f} {gb_per_dollar:<10} {capacity:<10}")
            return
          
      # If we couldn't parse the error or it's a different error, show the original message
      print(f"Error deploying instance: {str(e)}")
        
  except Exception as e:
    print(f"Error: {str(e)}")

def handle_ssh_keys(key_args: List[str]) -> List[str]:
  """Helper function to process SSH key arguments."""
  ssh_keys = []
  current_key = []
  in_quotes = False
  
  for arg in key_args:
    if arg.startswith('"') and arg.endswith('"'):
      # Handle key wrapped in quotes
      ssh_keys.append(arg.strip('"'))
    elif arg.startswith('"'):
      # Start of quoted key
      in_quotes = True
      current_key = [arg.strip('"')]
    elif arg.endswith('"'):
      # End of quoted key
      in_quotes = False
      current_key.append(arg.strip('"'))
      ssh_keys.append(' '.join(current_key))
      current_key = []
    elif in_quotes:
      # Middle of quoted key
      current_key.append(arg)
    else:
      # Regular unquoted key
      ssh_keys.append(arg)
  
  # Handle unclosed quotes
  if current_key:
    ssh_keys.append(' '.join(current_key))
    
  return ssh_keys

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

def listGPUs(settings: Settings, commands: List[str]) -> None:
  """
  Lists all available GPU configurations.
  
  Args:
      settings: Settings object containing API credentials
      commands: List of command arguments for sorting
  """
  try:
    api = MassedComputeAPI(settings)
    inventory = api.get_gpu_inventory()

    # Format and print GPU inventory
    print("\nAvailable GPU Configurations:")
    print("-" * 102)
    print(f"{'Product':<15} {'Description':<25} {'VRAM':<10} {'Price/Hr':<10} {'$/Hr/GB':<10} {'Available':<10}")
    print("-" * 102)

    # Prepare data for sorting
    gpu_data = []
    for product_info in inventory.values():
      instance_type = product_info.get('instance_type', {})
      name = instance_type.get('name', 'N/A')
      desc = instance_type.get('description', 'N/A')
      price = instance_type.get('price_cents_per_hour', 0) / 100
      capacity = product_info.get('capacity_available', 0)

      # Skip if sorting by available and capacity is 0
      if len(commands) > 3 and commands[3].lower().lstrip('-') in ['available', 'a'] and capacity == 0:
        continue

      # Calculate VRAM and $/Hr/GB if possible
      vram_amount = 0
      price_per_gb = 0
      vram_str = "N/A"
      price_per_gb_str = "N/A"
      
      for gpu_type, vram in GPU_VRAM.items():
        if gpu_type.lower() in name.lower():
          # Extract multiplier from name (1x, 2x, etc)
          multiplier = 1
          if "gpu_" in name.lower() and "x_" in name.lower():
            try:
              multiplier = int(name.split("x_")[0].split("gpu_")[1])
            except ValueError:
              pass
          vram_amount = vram * multiplier
          vram_str = f"{vram_amount}GB"
          if vram_amount > 0:
            price_per_gb = price/vram_amount
            price_per_gb_str = f"${price_per_gb:.3f}"
          break

      gpu_data.append({
        'name': name,
        'desc': desc,
        'vram': vram_amount,
        'vram_str': vram_str,
        'price': price,
        'price_per_gb': price_per_gb,
        'price_per_gb_str': price_per_gb_str,
        'capacity': capacity
      })

    # Sort data if sort parameter is provided
    if len(commands) > 3:
      sort_by = commands[3].lower()
      reverse = True if sort_by.startswith('-') else False
      sort_by = sort_by.lstrip('-')
      
      sort_key = None
      if sort_by in ['price', 'p']:
        sort_key = 'price'
      elif sort_by in ['vram', 'v']:
        sort_key = 'vram'
      elif sort_by in ['value', 'val']:
        sort_key = 'price_per_gb'
      elif sort_by in ['available', 'a']:
        sort_key = 'capacity'
        
      if sort_key:
        gpu_data.sort(key=lambda x: x[sort_key], reverse=reverse)
      else:
        print(f"\nUnknown sort parameter: {sort_by}")
        print("Available sort options:")
        print("  price, p       - Sort by price per hour")
        print("  vram, v        - Sort by total VRAM")
        print("  value, val     - Sort by $/Hr/GB")
        print("  available, a   - Sort by available capacity (hides unavailable)")
        print("Add '-' prefix for reverse sort (e.g., -price)")
        return

    # Print sorted data
    for gpu in gpu_data:
      print(f"{gpu['name'][:15]:<15} {gpu['desc'][:25]:<25} {gpu['vram_str']:<10} "
            f"${gpu['price']:<9.2f} {gpu['price_per_gb_str']:<10} {gpu['capacity']:<10}")

  except Exception as e:
    print(f"Error listing GPU inventory: {str(e)}")

def terminateInstances(settings: Settings, args: list[str]) -> None:
  """Terminates one or more instances by UUID or name."""
  if not args:
    print("Error: Must specify at least one instance UUID or name to terminate")
    return

  try:
    api = MassedComputeAPI(settings)
    instances = api.get_instances()
    uuids_to_terminate = []
    
    # Process each argument (UUID or name)
    for identifier in args:
      # Check if it matches any instance names
      matching_instances = [i for i in instances if i.get('name') == identifier]
      
      if matching_instances:
        if len(matching_instances) > 1:
          print(f"\nWarning: Multiple instances found with name '{identifier}':")
          for inst in matching_instances:
            print(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
          print("Please use UUID to terminate specific instance")
          continue
        else:
          instance_uuid = matching_instances[0].get('uuid')
          instance_name = matching_instances[0].get('name')
          print(f"Found instance '{instance_name}' with UUID: {instance_uuid}")
          uuids_to_terminate.append(instance_uuid)
      else:
        # Assume it's a UUID
        uuids_to_terminate.append(identifier)
    
    if not uuids_to_terminate:
      print("No valid instances found to terminate")
      return
      
    # Confirm termination
    print("\nPreparing to terminate the following instances:")
    for uuid in uuids_to_terminate:
      matching = next((i for i in instances if i.get('uuid') == uuid), None)
      if matching:
        print(f"  {matching.get('name')} ({uuid})")
      else:
        print(f"  {uuid}")
        
    confirm = input("\nAre you sure you want to terminate these instances? (y/N): ")
    if confirm.lower() != 'y':
      print("Termination cancelled")
      return
    
    # Proceed with termination
    response = api.terminate_instances(uuids_to_terminate)
    
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

def getInstanceDetails(settings: Settings, identifier: str) -> None:
  """
  Gets detailed information about a specific instance.
  
  Args:
      identifier: Either UUID or name of the instance to query
  """
  try:
    api = MassedComputeAPI(settings)
    
    # First try to get instance directly if UUID was provided
    instance = None
    try:
      instance = api.get_instance_details(identifier)
    except:
      # If that fails, try to find instance by name
      instances = api.get_instances()
      matching_instances = [i for i in instances if i.get('name') == identifier]
      
      if len(matching_instances) > 1:
        print(f"\nMultiple instances found with name '{identifier}':")
        for inst in matching_instances:
          print(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
        print("Please use UUID to get details of specific instance")
        return
      elif len(matching_instances) == 1:
        instance = matching_instances[0]
    
    if not instance:
      print(f"No instance found with identifier: {identifier}")
      return
      
    # Print basic info
    print("\nInstance Details:")
    print("-" * 72)
    print(f"Name: {instance.get('name', 'N/A')}")
    print(f"UUID: {instance.get('uuid', 'N/A')}")
    print(f"Status: {instance.get('status', 'N/A')}")
    print(f"IP Address: {instance.get('ip', 'N/A')}")
    print(f"Username: {instance.get('username', 'N/A')}")
    print(f"Password: {instance.get('password', 'N/A')}")
    print(f"Created: {instance.get('created', 'N/A')}")
    
    # Print startup command if present
    startup_cmd = instance.get('command_startup')
    if startup_cmd:
      print(f"Startup Command: {startup_cmd}")
    
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

def sshToInstance(settings: Settings, identifier: str) -> None:
  """
  Initiates an SSH session to the specified instance.
  
  Args:
      identifier: Either UUID or name of the instance to connect to
  """
  try:
    api = MassedComputeAPI(settings)
    
    # First try to get instance directly if UUID was provided
    instance = None
    try:
      instance = api.get_instance_details(identifier)
    except:
      # If that fails, try to find instance by name
      instances = api.get_instances()
      matching_instances = [i for i in instances if i.get('name') == identifier]
      
      if len(matching_instances) > 1:
        print(f"Multiple instances found with name '{identifier}':")
        for inst in matching_instances:
          print(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
        print("Please use UUID to connect to specific instance")
        return
      elif len(matching_instances) == 1:
        instance = matching_instances[0]
    
    if not instance:
      print(f"No instance found with identifier: {identifier}")
      return
      
    ip = instance.get('ip')
    username = instance.get('username')
    password = instance.get('password')
    name = instance.get('name')
    
    if not all([ip, username, password]):
      print("Error: Missing connection details for instance")
      return
      
    print(f"\nConnecting to {name} ({username}@{ip})...")
    
    # Construct sshpass command based on platform
    if platform.system() == "Windows":
      print("Connection details:")
      print(f"  Host: {ip}")
      print(f"  Username: {username}")
      print(f"  Password: {password}")
      print("\nPlease use these credentials in your SSH client")
      return
    
    # For Unix-like systems, use sshpass
    ssh_command = [
      "sshpass",
      "-p",
      password,
      "ssh",
      "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
      "-o", "StrictHostKeyChecking=no",
      "-o", "UserKnownHostsFile=/dev/null",
      f"{username}@{ip}"
    ]
    
    try:
      subprocess.run(ssh_command)
    except FileNotFoundError:
      print("Error: 'sshpass' is required but not installed.")
      print("Install it with:")
      if platform.system() == "Darwin":  # macOS
        print("  brew install hudochenkov/sshpass/sshpass")
      else:  # Linux
        print("  sudo apt-get install sshpass  # Ubuntu/Debian")
        print("  sudo yum install sshpass      # CentOS/RHEL")
    
  except Exception as e:
    print(f"Error connecting to instance: {str(e)}")

def runScript(settings: Settings, identifier: str, script_name: str) -> None:
  """
  Runs a predefined script on an existing instance using SSH.
  
  Args:
      identifier: UUID or name of the instance
      script_name: Name of the script to run
  """
  try:
    api = MassedComputeAPI(settings)
    
    # Get instance details
    instance = None
    try:
      instance = api.get_instance_details(identifier)
    except:
      instances = api.get_instances()
      matching_instances = [i for i in instances if i.get('name') == identifier]
      
      if len(matching_instances) > 1:
        print(f"\nMultiple instances found with name '{identifier}':")
        for inst in matching_instances:
          print(f"  {inst.get('name')} (UUID: {inst.get('uuid')})")
        print("Please use UUID to run script on specific instance")
        return
      elif len(matching_instances) == 1:
        instance = matching_instances[0]
    
    if not instance:
      print(f"No instance found with identifier: {identifier}")
      return
    
    # Get script
    script = get_startup_script(script_name.lower(), settings)
    if script is None:
      print(f"Unknown script: {script_name}")
      print("Available scripts:", ", ".join(STARTUP_SCRIPTS.keys()))
      return
    
    ip = instance.get('ip')
    username = instance.get('username')
    password = instance.get('password')
    name = instance.get('name')
    
    if not all([ip, username, password]):
      print("Error: Missing connection details for instance")
      return
      
    print(f"\nRunning script '{script_name}' on instance '{name}'...")
    
    # For Windows, show manual instructions
    if platform.system() == "Windows":
      print("\nWindows detected. Please run these commands in your SSH client:")
      print(f"Host: {ip}")
      print(f"Username: {username}")
      print(f"Password: {password}")
      print("\nCommands to run:")
      print(script)
      return
    
    # For Unix-like systems, use sshpass to execute the script
    ssh_command = [
      "sshpass",
      "-p",
      password,
      "ssh",
      "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
      "-o", "StrictHostKeyChecking=no",
      "-o", "UserKnownHostsFile=/dev/null",
      f"{username}@{ip}",
      script
    ]
    
    try:
      result = subprocess.run(ssh_command, capture_output=True, text=True)
      if result.returncode == 0:
        print("\nScript executed successfully")
        if result.stdout:
          print("\nOutput:")
          print(result.stdout)
      else:
        print("\nScript execution failed")
        if result.stderr:
          print("\nError output:")
          print(result.stderr)
    except FileNotFoundError:
      print("Error: 'sshpass' is required but not installed.")
      print("Install it with:")
      if platform.system() == "Darwin":  # macOS
        print("  brew install hudochenkov/sshpass/sshpass")
      else:  # Linux
        print("  sudo apt-get install sshpass  # Ubuntu/Debian")
        print("  sudo yum install sshpass      # CentOS/RHEL")
    
  except Exception as e:
    print(f"Error running script: {str(e)}")

##################################################
#                     API                        #
##################################################
# This class is responsible for interacting with the MassedCompute API.
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
    startup_script: Optional[str] = None,
    ssh_keys: Optional[List[str]] = None
  ) -> Dict[str, Any]:
    """
    Deploy the cheapest available GPU instance.
    
    Args:
        image_id: The ID of the image to deploy
        instance_name: Optional name for the instance
        startup_script: Optional startup script to run on instance launch
        ssh_keys: Optional list of SSH key names to add to the instance
        
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
    
    if ssh_keys:
      deploy_data["sshKey"] = ssh_keys

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

  def deploy_specific_instance(
    self,
    image_id: int,
    product_name: str,
    instance_name: Optional[str] = None,
    startup_script: Optional[str] = None,
    ssh_keys: Optional[List[str]] = None
  ) -> Dict[str, Any]:
    """
    Deploy a specific GPU instance type.
    
    Args:
        image_id: The ID of the image to deploy
        product_name: The specific product name to deploy
        instance_name: Optional name for the instance
        startup_script: Optional startup script to run on instance launch
        ssh_keys: Optional list of SSH key names to add to the instance
        
    Returns:
        Dict containing the deployment response with instance UUID
    """
    deploy_data = {
      "imageId": image_id,
      "productName": product_name,
      "regionName": "any"
    }
    
    if instance_name:
      deploy_data["instanceName"] = instance_name
      
    if startup_script:
      deploy_data["command"] = startup_script
    
    if ssh_keys:
      deploy_data["sshKey"] = ssh_keys

    deploy_response = requests.post(
      f"{self.base_url}/instance/launch",
      headers=self.headers,
      json=deploy_data
    )
    deploy_response.raise_for_status()
    
    return deploy_response.json()
